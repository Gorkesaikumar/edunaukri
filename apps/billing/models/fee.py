from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.billing.constants.enums import FeeScopeType, FeeType, PlacementFeeStatus
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.models.base import AuditedBaseModel


class FeeSchedule(AuditedBaseModel):
    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    name = models.CharField(max_length=200)
    fee_type = models.CharField(
        max_length=20, choices=FeeType.choices, default=FeeType.PERCENTAGE
    )
    scope_type = models.CharField(
        max_length=20,
        choices=FeeScopeType.choices,
        default=FeeScopeType.GLOBAL,
        db_index=True,
    )
    scope_id = models.UUIDField(null=True, blank=True, db_index=True)
    percentage_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    fixed_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="INR")
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_until = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "billing_fee_schedule"

    def __str__(self):
        return f"{self.name} ({self.domain})"


class PlacementFee(AuditedBaseModel):
    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    entity_type = models.CharField(
        max_length=40, choices=EntityReferenceType.choices, db_index=True
    )
    entity_id = models.UUIDField(db_index=True)
    fee_schedule = models.ForeignKey(
        FeeSchedule, on_delete=models.PROTECT, related_name="placement_fees"
    )
    base_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    calculated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(
        max_length=20,
        choices=PlacementFeeStatus.choices,
        default=PlacementFeeStatus.PENDING,
        db_index=True,
    )
    bill_to_entity_type = models.CharField(
        max_length=40, choices=EntityReferenceType.choices
    )
    bill_to_entity_id = models.UUIDField(db_index=True)
    bill_to_name_snapshot = models.CharField(max_length=300)
    entity_title_snapshot = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "billing_placement_fee"
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "entity_type", "entity_id"],
                condition=models.Q(is_deleted=False),
                name="unique_active_placement_fee",
            ),
        ]

    def __str__(self):
        return f"{self.calculated_amount} {self.currency} — {self.entity_type}"
