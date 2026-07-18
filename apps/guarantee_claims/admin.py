from django.contrib import admin

from apps.guarantee_claims.models import (
    GuaranteeClaim,
    GuaranteeClaimHistory,
    PlacementGuarantee,
)


@admin.register(PlacementGuarantee)
class PlacementGuaranteeAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_id",
        "domain",
        "status",
        "guarantee_days",
        "starts_at",
        "expires_at",
    )
    list_filter = ("domain", "status", "is_deleted")


@admin.register(GuaranteeClaim)
class GuaranteeClaimAdmin(admin.ModelAdmin):
    list_display = (
        "claim_number",
        "claim_type",
        "domain",
        "status",
        "resolution",
        "invoice_id",
        "submitted_at",
        "resolved_at",
    )
    list_filter = ("domain", "claim_type", "status", "resolution", "is_deleted")
    search_fields = ("claim_number", "reason")


@admin.register(GuaranteeClaimHistory)
class GuaranteeClaimHistoryAdmin(admin.ModelAdmin):
    list_display = ("claim", "from_status", "to_status", "changed_at")
    readonly_fields = (
        "claim",
        "from_status",
        "to_status",
        "changed_by_id",
        "notes",
        "changed_at",
    )


from apps.guarantee_claims.models.placement_claim import PlacementClaim, PlacementClaimHistory
from apps.guarantee_claims.services.placement_claim_service import PlacementClaimService
from apps.guarantee_claims.constants.enums import PlacementClaimStatus
from django.contrib import messages

@admin.action(description="Approve selected claims")
def approve_claims(modeladmin, request, queryset):
    service = PlacementClaimService()
    success_count = 0
    for claim in queryset:
        try:
            service.approve_claim(claim, request.user.pk)
            success_count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Failed to approve {claim.claim_number}: {e}", level=messages.ERROR)
    
    if success_count:
        modeladmin.message_user(request, f"Successfully approved {success_count} claims.", level=messages.SUCCESS)

@admin.action(description="Reject selected claims")
def reject_claims(modeladmin, request, queryset):
    service = PlacementClaimService()
    success_count = 0
    for claim in queryset:
        try:
            # Simple rejection for bulk action. For detailed rejection, admin form should be used.
            service.reject_claim(claim, request.user.pk, "Rejected by admin action")
            success_count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Failed to reject {claim.claim_number}: {e}", level=messages.ERROR)
            
    if success_count:
        modeladmin.message_user(request, f"Successfully rejected {success_count} claims.", level=messages.SUCCESS)

@admin.action(description="Request More Information")
def request_more_info(modeladmin, request, queryset):
    for claim in queryset:
        if claim.status == PlacementClaimStatus.UNDER_REVIEW:
            claim.status = PlacementClaimStatus.MORE_INFORMATION_REQUIRED
            claim.save(update_fields=['status'])
            PlacementClaimHistory.objects.create(
                claim=claim,
                from_status=PlacementClaimStatus.UNDER_REVIEW,
                to_status=PlacementClaimStatus.MORE_INFORMATION_REQUIRED,
                notes="Admin requested more information."
            )
    modeladmin.message_user(request, "Status updated to More Information Required.", level=messages.SUCCESS)

@admin.register(PlacementClaim)
class PlacementClaimAdmin(admin.ModelAdmin):
    list_display = (
        "claim_number",
        "application",
        "institution",
        "status",
        "claim_reason",
        "incident_date",
        "refund_amount",
        "submitted_at",
    )
    list_filter = ("status", "claim_reason", "institution")
    search_fields = ("claim_number", "application__vacancy__title", "institution__name")
    readonly_fields = ("claim_number", "submitted_at", "reviewed_at", "approved_at", "rejected_at", "refund_amount")
    actions = [approve_claims, reject_claims, request_more_info]

@admin.register(PlacementClaimHistory)
class PlacementClaimHistoryAdmin(admin.ModelAdmin):
    list_display = ("claim", "from_status", "to_status", "changed_at")
    readonly_fields = ("claim", "from_status", "to_status", "changed_by_id", "notes", "changed_at")

