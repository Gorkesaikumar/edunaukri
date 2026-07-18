from rest_framework import serializers

from apps.billing.constants.enums import FeeScopeType, FeeType
from apps.billing.models import FeeSchedule, PlacementFee


class FeeScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeSchedule
        fields = (
            "id",
            "domain",
            "name",
            "fee_type",
            "scope_type",
            "scope_id",
            "percentage_rate",
            "fixed_amount",
            "currency",
            "is_active",
            "effective_from",
            "effective_until",
            "description",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class FeeScheduleCreateSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(
        choices=FeeSchedule._meta.get_field("domain").choices
    )
    name = serializers.CharField(max_length=200)
    fee_type = serializers.ChoiceField(choices=FeeType.choices)
    scope_type = serializers.ChoiceField(
        choices=FeeScopeType.choices, required=False, default=FeeScopeType.GLOBAL
    )
    scope_id = serializers.UUIDField(required=False, allow_null=True)
    percentage_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    fixed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    currency = serializers.CharField(max_length=3, required=False, default="INR")
    description = serializers.CharField(required=False, allow_blank=True)


class PlacementFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementFee
        fields = (
            "id",
            "domain",
            "entity_type",
            "entity_id",
            "fee_schedule",
            "base_amount",
            "calculated_amount",
            "currency",
            "status",
            "bill_to_entity_type",
            "bill_to_entity_id",
            "bill_to_name_snapshot",
            "entity_title_snapshot",
            "created_at",
        )
        read_only_fields = fields
