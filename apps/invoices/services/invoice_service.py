import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.billing.constants.enums import PlacementFeeStatus
from apps.billing.models import PlacementFee
from apps.billing.repositories.fee_repository import PlacementFeeRepository
from apps.core.middleware.audit_context import get_audit_actor
from apps.core.services.base import BaseService
from apps.invoices.constants.enums import InvoiceStatus
from apps.invoices.models import Invoice
from apps.invoices.repositories.invoice_repository import (
    InvoiceLineItemRepository,
    InvoiceRepository,
)
from apps.invoices.services.invoice_lifecycle_service import InvoiceLifecycleService
from apps.invoices.services.payment_tracking_service import PaymentTrackingService


class InvoiceGenerationService(BaseService):
    def __init__(self):
        self.invoice_repository = InvoiceRepository()
        self.line_item_repository = InvoiceLineItemRepository()
        self.placement_fee_repository = PlacementFeeRepository()

    @transaction.atomic
    def generate_from_placement_fee(self, placement_fee: PlacementFee) -> Invoice:
        if placement_fee.status == PlacementFeeStatus.INVOICED:
            raise ValidationError("Placement fee is already invoiced.")
        if placement_fee.status != PlacementFeeStatus.PENDING:
            raise ValidationError("Only pending placement fees can be invoiced.")

        invoice = self.invoice_repository.create(
            invoice_number=self._next_invoice_number(),
            domain=placement_fee.domain,
            placement_fee_id=placement_fee.pk,
            bill_to_entity_type=placement_fee.bill_to_entity_type,
            bill_to_entity_id=placement_fee.bill_to_entity_id,
            bill_to_name_snapshot=placement_fee.bill_to_name_snapshot,
            subtotal=placement_fee.calculated_amount,
            total_amount=placement_fee.calculated_amount,
            currency=placement_fee.currency,
            created_by_id=placement_fee.created_by_id,
        )
        self.line_item_repository.create(
            invoice=invoice,
            description=f"Placement fee — {placement_fee.entity_title_snapshot or placement_fee.entity_type}",
            quantity=Decimal("1"),
            unit_price=placement_fee.calculated_amount,
            line_total=placement_fee.calculated_amount,
            created_by_id=placement_fee.created_by_id,
        )
        self.placement_fee_repository.update(
            placement_fee, status=PlacementFeeStatus.INVOICED
        )
        return invoice

    def _next_invoice_number(self) -> str:
        prefix = timezone.now().strftime("INV-%Y%m")
        suffix = uuid.uuid4().hex[:8].upper()
        return f"{prefix}-{suffix}"


class InvoiceService(BaseService):
    """Facade for invoice lifecycle operations."""

    def __init__(self):
        self.lifecycle = InvoiceLifecycleService()

    @transaction.atomic
    def issue(self, invoice: Invoice, *, due_days: int = 30) -> Invoice:
        return self.lifecycle.issue(invoice, due_days=due_days)

    @transaction.atomic
    def cancel(self, invoice: Invoice, *, notes: str = "") -> Invoice:
        return self.lifecycle.cancel(invoice, notes=notes)


class PaymentRecordingService(BaseService):
    """Backward-compatible alias for payment tracking."""

    def __init__(self):
        self.tracking = PaymentTrackingService()

    @transaction.atomic
    def record_payment(self, invoice: Invoice, **kwargs):
        return self.tracking.record_payment(invoice, **kwargs)
