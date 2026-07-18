from django.utils import timezone

from apps.core.services.base import BaseService
from apps.guarantee_claims.constants.enums import (
    DEFAULT_GUARANTEE_DAYS,
    GuaranteeStatus,
)
from apps.guarantee_claims.models import PlacementGuarantee
from apps.guarantee_claims.repositories.claim_repository import GuaranteeRepository


class GuaranteeService(BaseService):
    """Creates and manages placement guarantee windows."""

    def __init__(self):
        self.repository = GuaranteeRepository()

    def ensure_for_invoice(
        self,
        *,
        invoice,
        application_entity_type: str,
        application_entity_id,
        domain: str,
        guarantee_days: int = None,
    ) -> PlacementGuarantee | None:
        existing = self.repository.filter_by(invoice_id=invoice.pk).first()
        if existing:
            return existing

        if guarantee_days is None:
            from apps.core.services.config import get_setting

            guarantee_days = get_setting(
                "billing.guarantee_days", {"days": DEFAULT_GUARANTEE_DAYS}
            ).get("days", DEFAULT_GUARANTEE_DAYS)

        now = timezone.now()
        return self.repository.create(
            domain=domain,
            invoice_id=invoice.pk,
            placement_fee_id=invoice.placement_fee_id,
            application_entity_type=application_entity_type,
            application_entity_id=application_entity_id,
            guarantee_days=guarantee_days,
            starts_at=now,
            expires_at=now + timezone.timedelta(days=guarantee_days),
            status=GuaranteeStatus.ACTIVE,
        )

    def is_within_guarantee(self, guarantee: PlacementGuarantee) -> bool:
        if guarantee.status != GuaranteeStatus.ACTIVE:
            return False
        return timezone.now() <= guarantee.expires_at

    def mark_claimed(self, guarantee: PlacementGuarantee) -> PlacementGuarantee:
        return self.repository.update(guarantee, status=GuaranteeStatus.CLAIMED)

    def close(self, guarantee: PlacementGuarantee) -> PlacementGuarantee:
        return self.repository.update(guarantee, status=GuaranteeStatus.CLOSED)
