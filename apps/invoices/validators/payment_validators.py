"""Payment entry validators."""

from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.invoices.constants.enums import PaymentStatus


def validate_payment_amount(amount: Decimal) -> None:
    if amount <= 0:
        raise ValidationError("Payment amount must be positive.")


def validate_payment_status(status: str) -> None:
    if status not in PaymentStatus.values:
        raise ValidationError("Invalid payment status.")
