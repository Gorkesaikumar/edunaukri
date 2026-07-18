from apps.billing.models import FeeSchedule, PlacementFee
from apps.core.repositories.crud import CRUDRepository


class FeeScheduleRepository(CRUDRepository):
    model = FeeSchedule


class PlacementFeeRepository(CRUDRepository):
    model = PlacementFee
