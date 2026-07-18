from decimal import Decimal

from django.utils import timezone

from apps.core.middleware.audit_context import get_audit_actor
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.invoices.constants.enums import InvoiceStatus
from apps.invoices.models import Invoice
from apps.invoices.repositories.invoice_repository import (
    InvoiceRepository,
    InvoiceStatusHistoryRepository,
    RefundRecordRepository,
)
from apps.invoices.validators.invoice_validators import validate_can_refund


class RefundService(BaseService):
    """Process invoice refunds with audit history."""

    def __init__(self):
        self.invoice_repository = InvoiceRepository()
        self.refund_repository = RefundRecordRepository()
        self.history_repository = InvoiceStatusHistoryRepository()
        self.outbox = OutboxService()

    @BaseService.atomic
    def refund(
        self,
        invoice: Invoice,
        *,
        amount: Decimal,
        reason: str,
        reference_number: str = "",
        notes: str = "",
    ):
        validate_can_refund(invoice, amount)
        actor = get_audit_actor()
        refund = self.refund_repository.create(
            invoice=invoice,
            amount=amount,
            reason=reason,
            reference_number=reference_number,
            notes=notes,
            processed_by_id=actor.actor_id if actor else None,
            created_by_id=actor.actor_id if actor else None,
        )
        previous_status = invoice.status
        invoice = self.invoice_repository.update(
            invoice,
            status=InvoiceStatus.REFUNDED,
            refunded_at=timezone.now(),
        )
        self.history_repository.create(
            invoice=invoice,
            from_status=previous_status,
            to_status=invoice.status,
            changed_by_id=actor.actor_id if actor else None,
            notes=reason,
        )
        self.outbox.publish(
            domain=invoice.domain,
            event_type="invoice.refunded",
            aggregate_type="billing_invoice",
            aggregate_id=invoice.pk,
            payload={
                "invoice_id": str(invoice.pk),
                "refund_amount": str(amount),
                "reason": reason,
            },
        )
        return refund
