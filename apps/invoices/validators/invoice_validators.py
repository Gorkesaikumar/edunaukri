"""Invoice field and lifecycle validators."""

from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.invoices.constants.enums import TERMINAL_INVOICE_STATUSES, InvoiceStatus


def validate_can_issue(invoice) -> None:
    if invoice.status != InvoiceStatus.DRAFT:
        raise ValidationError("Only draft invoices can be issued.")


def validate_can_cancel(invoice) -> None:
    if invoice.status in (
        InvoiceStatus.PAID,
        InvoiceStatus.CANCELLED,
        InvoiceStatus.REFUNDED,
    ):
        raise ValidationError("Paid or terminal invoices cannot be cancelled.")
    if invoice.status == InvoiceStatus.VOID:
        raise ValidationError("Void invoices cannot be cancelled.")


def validate_can_record_payment(invoice, amount: Decimal) -> None:
    from apps.invoices.validators.payment_validators import validate_payment_amount

    if invoice.status in TERMINAL_INVOICE_STATUSES:
        raise ValidationError("Cannot record payment on a terminal invoice.")
    validate_payment_amount(amount)


def validate_can_refund(invoice, amount: Decimal) -> None:
    from apps.invoices.validators.refund_validators import validate_refund_request

    validate_refund_request(invoice, amount)
