from typing import List
from apps.core.services.base import BaseService
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.guarantee_claims.constants.enums import ClaimStatus
from django.db.models import QuerySet

class GuaranteeClaimQueryService(BaseService):
    
    @classmethod
    def get_operational_claims(cls) -> QuerySet[GuaranteeClaim]:
        """
        Returns all active operational claims.
        Excludes archived or data-corrupted claims.
        """
        return GuaranteeClaim.objects.exclude(
            status__in=[ClaimStatus.INVALID_DATA, ClaimStatus.ARCHIVED]
        ).order_by("-created_at")
