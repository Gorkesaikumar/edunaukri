"""Guarantee period validators."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.guarantee_claims.constants.enums import GuaranteeStatus


def validate_guarantee_active(guarantee) -> None:
    if not guarantee:
        raise ValidationError("No guarantee record found for this invoice.")
    if guarantee.status != GuaranteeStatus.ACTIVE:
        raise ValidationError("Guarantee is not active.")
    if timezone.now() > guarantee.expires_at:
        raise ValidationError("Guarantee period has expired.")
