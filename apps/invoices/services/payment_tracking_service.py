from decimal import Decimal

from django.utils import timezone

from apps.core.middleware.audit_context import get_audit_actor
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.invoices.constants.enums import InvoiceStatus, PaymentStatus
from apps.invoices.models import Invoice
from apps.invoices.repositories.invoice_repository import (
    InvoiceRepository,
    InvoiceStatusHistoryRepository,
    PaymentRecordRepository,
)
from apps.invoices.validators.invoice_validators import validate_can_record_payment


class PaymentTrackingService(BaseService):
    """Manual payment entry and status tracking."""

    def __init__(self):
        self.invoice_repository = InvoiceRepository()
        self.payment_repository = PaymentRecordRepository()
        self.history_repository = InvoiceStatusHistoryRepository()
        self.outbox = OutboxService()

    @BaseService.atomic
    def record_payment(
        self,
        invoice: Invoice,
        *,
        amount: Decimal,
        payment_method: str,
        reference_number: str = "",
        notes: str = "",
        status: str = PaymentStatus.PAID,
    ):
        validate_can_record_payment(invoice, amount)
        actor = get_audit_actor()
        payment = self.payment_repository.create(
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            status=status,
            reference_number=reference_number,
            notes=notes,
            recorded_by_id=actor.actor_id if actor else None,
            created_by_id=actor.actor_id if actor else None,
        )

        amount_paid = (invoice.amount_paid or Decimal("0")) + amount
        previous_status = invoice.status
        if amount_paid >= invoice.total_amount:
            invoice = self.invoice_repository.update(
                invoice,
                amount_paid=amount_paid,
                status=InvoiceStatus.PAID,
                paid_at=timezone.now(),
            )
            self._publish_paid(invoice)
        else:
            invoice = self.invoice_repository.update(
                invoice,
                amount_paid=amount_paid,
                status=InvoiceStatus.PARTIALLY_PAID,
            )
        self.history_repository.create(
            invoice=invoice,
            from_status=previous_status,
            to_status=invoice.status,
            changed_by_id=actor.actor_id if actor else None,
            notes=notes or f"Payment recorded: {amount}",
        )
        return payment

    def _publish_paid(self, invoice: Invoice) -> None:
        self.outbox.publish(
            domain=invoice.domain,
            event_type="invoice.paid",
            aggregate_type="billing_invoice",
            aggregate_id=invoice.pk,
            payload={
                "invoice_id": str(invoice.pk),
                "invoice_number": invoice.invoice_number,
                "recipient_domain": "college" if invoice.domain == "faculty" else "it",
                "recipient_id": str(invoice.bill_to_entity_id),
                "title": "Invoice paid",
                "body": f"Invoice {invoice.invoice_number} has been paid in full.",
            },
        )
