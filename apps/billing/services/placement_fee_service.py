from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.billing.constants.enums import FeeType, FeeScopeType, PlacementFeeStatus
from apps.billing.models import FeeSchedule, PlacementFee
from apps.billing.repositories.fee_repository import (
    FeeScheduleRepository,
    PlacementFeeRepository,
)
from apps.billing.selectors.fee_selector import FeeScheduleSelector
from apps.core.services.base import BaseService


class FeeScheduleService(BaseService):
    def __init__(self):
        self.repository = FeeScheduleRepository()

    @transaction.atomic
    def create_schedule(self, *, data: dict, created_by_id=None) -> FeeSchedule:
        fee_type = data.get("fee_type", FeeType.PERCENTAGE)
        if fee_type == FeeType.PERCENTAGE and not data.get("percentage_rate"):
            raise ValidationError(
                "Percentage rate is required for percentage fee schedules."
            )
        if fee_type == FeeType.FIXED and not data.get("fixed_amount"):
            raise ValidationError("Fixed amount is required for fixed fee schedules.")

        return self.repository.create(
            domain=data["domain"],
            name=data["name"],
            fee_type=fee_type,
            scope_type=data.get("scope_type", FeeScopeType.GLOBAL),
            scope_id=data.get("scope_id"),
            percentage_rate=data.get("percentage_rate"),
            fixed_amount=data.get("fixed_amount"),
            currency=data.get("currency", "INR"),
            is_active=data.get("is_active", True),
            effective_from=data.get("effective_from") or timezone.now(),
            effective_until=data.get("effective_until"),
            description=data.get("description", ""),
            created_by_id=created_by_id,
        )


class FeeCalculationService(BaseService):
    def calculate(
        self, *, schedule: FeeSchedule, base_amount: Decimal | None
    ) -> Decimal:
        if schedule.fee_type == FeeType.FIXED:
            return schedule.fixed_amount or Decimal("0")

        if not base_amount:
            raise ValidationError(
                "Base amount is required for percentage fee calculation."
            )
        rate = schedule.percentage_rate or Decimal("0")
        return (base_amount * rate / Decimal("100")).quantize(Decimal("0.01"))


class PlacementFeeService(BaseService):
    def __init__(self):
        self.repository = PlacementFeeRepository()
        self.schedule_selector = FeeScheduleSelector()

    def get_active_schedule(
        self,
        domain: str,
        *,
        bill_to_entity_type: str | None = None,
        bill_to_entity_id=None,
    ) -> FeeSchedule | None:
        return self.schedule_selector.active_for_placement(
            domain,
            bill_to_entity_type=bill_to_entity_type,
            bill_to_entity_id=bill_to_entity_id,
        )

    @transaction.atomic
    def create_for_placed_application(
        self,
        *,
        domain: str,
        entity_type: str,
        entity_id,
        entity_title: str,
        bill_to_entity_type: str,
        bill_to_entity_id,
        bill_to_name: str,
        base_amount=None,
        created_by_id=None,
    ) -> PlacementFee | None:
        if self.repository.exists(
            domain=domain, entity_type=entity_type, entity_id=entity_id
        ):
            return None

        schedule = self.get_active_schedule(
            domain,
            bill_to_entity_type=bill_to_entity_type,
            bill_to_entity_id=bill_to_entity_id,
        )
        if not schedule:
            return None

        calculated = FeeCalculationService().calculate(
            schedule=schedule,
            base_amount=Decimal(str(base_amount)) if base_amount is not None else None,
        )

        return self.repository.create(
            domain=domain,
            entity_type=entity_type,
            entity_id=entity_id,
            fee_schedule=schedule,
            base_amount=base_amount,
            calculated_amount=calculated,
            currency=schedule.currency,
            bill_to_entity_type=bill_to_entity_type,
            bill_to_entity_id=bill_to_entity_id,
            bill_to_name_snapshot=bill_to_name,
            entity_title_snapshot=entity_title,
            created_by_id=created_by_id,
        )
