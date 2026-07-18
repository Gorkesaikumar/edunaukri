"""Refund validators."""

from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.invoices.constants.enums import InvoiceStatus


def validate_refund_request(invoice, amount: Decimal) -> None:
    if invoice.status != InvoiceStatus.PAID:
        raise ValidationError("Only paid invoices can be refunded.")
    if amount <= 0:
        raise ValidationError("Refund amount must be positive.")
    if amount > invoice.amount_paid:
        raise ValidationError("Refund amount cannot exceed amount paid.")
