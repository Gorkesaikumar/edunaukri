from apps.core.repositories.crud import CRUDRepository
from apps.guarantee_claims.models import (
    GuaranteeClaim,
    GuaranteeClaimHistory,
    PlacementGuarantee,
)


class GuaranteeRepository(CRUDRepository):
    model = PlacementGuarantee


class GuaranteeClaimRepository(CRUDRepository):
    model = GuaranteeClaim


class GuaranteeClaimHistoryRepository(CRUDRepository):
    model = GuaranteeClaimHistory
