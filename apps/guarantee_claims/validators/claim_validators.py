"""Guarantee claim validators."""

from django.core.exceptions import ValidationError

from apps.guarantee_claims.constants.enums import ClaimStatus
from apps.guarantee_claims.models import GuaranteeClaim


from apps.guarantee_claims.validators.guarantee_validators import (
    validate_guarantee_active,
)


def validate_claim_within_guarantee(guarantee) -> None:
    validate_guarantee_active(guarantee)


def validate_no_active_claim(*, invoice_id, exclude_claim_id=None) -> None:
    qs = GuaranteeClaim.objects.filter(invoice_id=invoice_id, is_deleted=False).exclude(
        status__in=(ClaimStatus.REJECTED, ClaimStatus.RESOLVED)
    )
    if exclude_claim_id:
        qs = qs.exclude(pk=exclude_claim_id)
    if qs.exists():
        raise ValidationError(
            "An active guarantee claim already exists for this invoice."
        )
