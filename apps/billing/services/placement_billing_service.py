"""Orchestrates placement fee creation, invoice generation, and guarantee setup from domain events."""

from decimal import Decimal

from django.db import transaction

from apps.billing.constants.enums import PlacementFeeStatus
from apps.billing.repositories.fee_repository import PlacementFeeRepository
from apps.billing.services.placement_fee_service import PlacementFeeService
from apps.core.constants.enums import DomainType
from apps.core.models.outbox_event import OutboxEvent
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.guarantee_claims.services.guarantee_service import GuaranteeService
from apps.invoices.repositories.invoice_repository import InvoiceRepository
from apps.invoices.services.invoice_lifecycle_service import InvoiceLifecycleService
from apps.invoices.services.invoice_service import InvoiceGenerationService


class PlacementBillingService(BaseService):
    """Consumes hire/join events and produces placement fees, invoices, and guarantees."""

    def __init__(self):
        self.fee_service = PlacementFeeService()
        self.fee_repository = PlacementFeeRepository()
        self.invoice_repository = InvoiceRepository()
        self.invoice_generation = InvoiceGenerationService()
        self.invoice_lifecycle = InvoiceLifecycleService()
        self.guarantee_service = GuaranteeService()
        self.outbox = OutboxService()

    @transaction.atomic
    def handle_outbox_event(self, event: OutboxEvent) -> dict | None:
        billing = (event.payload or {}).get("billing")
        if not billing:
            return None
        return self.process_placement(
            domain=event.domain,
            entity_type=billing["entity_type"],
            entity_id=billing["entity_id"],
            entity_title=billing.get("entity_title", ""),
            bill_to_entity_type=billing["bill_to_entity_type"],
            bill_to_entity_id=billing["bill_to_entity_id"],
            bill_to_name=billing.get("bill_to_name", ""),
            base_amount=billing.get("base_amount"),
            created_by_id=billing.get("created_by_id"),
        )

    @transaction.atomic
    def process_placement(
        self,
        *,
        domain: str,
        entity_type: str,
        entity_id,
        entity_title: str,
        bill_to_entity_type: str,
        bill_to_entity_id,
        bill_to_name: str,
        base_amount=None,
        created_by_id=None,
    ) -> dict:
        
        # Determine application model
        application = None
        if entity_type == 'faculty_application':
            from apps.applications.models import FacultyApplication
            application = FacultyApplication.objects.filter(pk=entity_id).first()
        elif entity_type == 'it_job_application':
            from apps.applications.models import JobApplication
            application = JobApplication.objects.filter(pk=entity_id).first()
            
        if not application:
            return {"skipped": True, "reason": f"Application {entity_id} not found"}

        # Use unified PlacementInvoiceService to generate the invoice
        from apps.invoices.services.placement_invoice_service import PlacementInvoiceService
        
        try:
            invoice = PlacementInvoiceService().generate_for_selection(application)
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

        if not invoice:
            return {"skipped": True, "reason": "Invoice could not be generated"}

        if invoice.status == 'draft' or invoice.status == 'pending':
            invoice = self.invoice_lifecycle.issue(invoice)
            self._publish_invoice_issued(invoice)

        guarantee = self.guarantee_service.ensure_for_invoice(
            invoice=invoice,
            application_entity_type=entity_type,
            application_entity_id=entity_id,
            domain=domain,
        )

        return {
            "invoice_id": str(invoice.pk),
            "guarantee_id": str(guarantee.pk) if guarantee else None,
        }

    def _publish_invoice_issued(self, invoice) -> None:
        self.outbox.publish(
            domain=invoice.domain,
            event_type="invoice.issued",
            aggregate_type="billing_invoice",
            aggregate_id=invoice.pk,
            payload={
                "invoice_id": str(invoice.pk),
                "invoice_number": invoice.invoice_number,
                "bill_to_entity_type": invoice.bill_to_entity_type,
                "bill_to_entity_id": str(invoice.bill_to_entity_id),
                "bill_to_name": invoice.bill_to_name_snapshot,
                "total_amount": str(invoice.total_amount),
                "currency": invoice.currency,
                "recipient_domain": "college"
                if invoice.domain == DomainType.FACULTY
                else "it",
                "recipient_id": str(invoice.bill_to_entity_id),
                "title": "Invoice issued",
                "body": f"Invoice {invoice.invoice_number} for {invoice.total_amount} {invoice.currency} has been issued.",
            },
        )
