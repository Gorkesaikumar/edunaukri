from django.contrib import admin

from apps.billing.models import FeeSchedule, PlacementFee


@admin.register(FeeSchedule)
class FeeScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "domain",
        "fee_type",
        "scope_type",
        "scope_id",
        "percentage_rate",
        "fixed_amount",
        "is_active",
        "effective_from",
    )
    list_filter = ("domain", "fee_type", "scope_type", "is_active", "is_deleted")


@admin.register(PlacementFee)
class PlacementFeeAdmin(admin.ModelAdmin):
    list_display = (
        "entity_type",
        "entity_id",
        "calculated_amount",
        "currency",
        "status",
        "bill_to_name_snapshot",
    )
    list_filter = ("domain", "status", "is_deleted")
