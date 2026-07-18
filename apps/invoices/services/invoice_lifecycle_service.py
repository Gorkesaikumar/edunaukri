from django.utils import timezone

from apps.core.middleware.audit_context import get_audit_actor
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.invoices.constants.enums import InvoiceStatus
from apps.invoices.models import Invoice
from apps.invoices.repositories.invoice_repository import (
    InvoiceRepository,
    InvoiceStatusHistoryRepository,
)
from apps.invoices.selectors.invoice_selector import OutstandingInvoiceSelector


class InvoiceLifecycleService(BaseService):
    """Issue, cancel, and mark overdue invoices with immutable history."""

    def __init__(self):
        self.repository = InvoiceRepository()
        self.history_repository = InvoiceStatusHistoryRepository()
        self.overdue_selector = OutstandingInvoiceSelector()
        self.outbox = OutboxService()

    @BaseService.atomic
    def issue(self, invoice: Invoice, *, due_days: int = 30) -> Invoice:
        from apps.invoices.validators.invoice_validators import validate_can_issue

        validate_can_issue(invoice)
        current = invoice.status
        invoice = self.repository.update(
            invoice,
            status=InvoiceStatus.ISSUED,
            issued_at=timezone.now(),
            due_at=timezone.now() + timezone.timedelta(days=due_days),
        )
        self._record_history(invoice, current, invoice.status, "Invoice issued.")
        return invoice

    @BaseService.atomic
    def cancel(self, invoice: Invoice, *, notes: str = "") -> Invoice:
        from apps.invoices.validators.invoice_validators import validate_can_cancel

        validate_can_cancel(invoice)
        current = invoice.status
        invoice = self.repository.update(
            invoice,
            status=InvoiceStatus.CANCELLED,
            cancelled_at=timezone.now(),
        )
        self._record_history(
            invoice, current, invoice.status, notes or "Invoice cancelled."
        )
        self.outbox.publish(
            domain=invoice.domain,
            event_type="invoice.cancelled",
            aggregate_type="billing_invoice",
            aggregate_id=invoice.pk,
            payload={
                "invoice_id": str(invoice.pk),
                "invoice_number": invoice.invoice_number,
                "reason": notes or "Invoice cancelled.",
                "recipient_domain": "college" if invoice.domain == "faculty" else "it",
                "recipient_id": str(invoice.bill_to_entity_id),
                "title": "Invoice cancelled",
                "body": f"Invoice {invoice.invoice_number} has been cancelled.",
            },
        )
        return invoice

    @BaseService.atomic
    def mark_overdue(self, invoice: Invoice) -> Invoice | None:
        if invoice.status not in (
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.PENDING,
        ):
            return None
        if invoice.due_at and invoice.due_at > timezone.now():
            return None
        current = invoice.status
        invoice = self.repository.update(invoice, status=InvoiceStatus.OVERDUE)
        self._record_history(
            invoice, current, invoice.status, "Invoice marked overdue."
        )
        return invoice

    def mark_all_overdue(self, *, limit: int = 100) -> int:
        """Batch-mark past-due invoices as overdue."""
        marked = 0
        for invoice in self.overdue_selector.due_for_overdue_marking()[:limit]:
            if self.mark_overdue(invoice):
                marked += 1
        return marked

    def _record_history(self, invoice, from_status, to_status, notes="") -> None:
        actor = get_audit_actor()
        self.history_repository.create(
            invoice=invoice,
            from_status=from_status,
            to_status=to_status,
            changed_by_id=actor.actor_id if actor else None,
            notes=notes,
        )
