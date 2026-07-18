from django.db import models
from django.utils import timezone

from apps.applications.models import FacultyApplication, JobApplication
from apps.colleges.models import College
from apps.core.models.base import AuditedBaseModel
from apps.guarantee_claims.constants.enums import PlacementClaimReason, PlacementClaimStatus
from apps.invoices.models import Invoice


class PlacementClaim(AuditedBaseModel):
    claim_number = models.CharField(max_length=50, unique=True)
    application = models.ForeignKey(
        FacultyApplication, on_delete=models.PROTECT, related_name="placement_claims", null=True, blank=True
    )
    job_application = models.ForeignKey(
        JobApplication, on_delete=models.PROTECT, related_name="placement_claims", null=True, blank=True
    )
    claim_type = models.CharField(
        max_length=20,
        choices=[("refund", "Refund"), ("replacement", "Replacement")],
        default="refund"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="placement_claims", null=True, blank=True
    )
    institution = models.ForeignKey(
        College, on_delete=models.PROTECT, related_name="placement_claims", null=True, blank=True
    )
    company_id = models.UUIDField(null=True, blank=True, db_index=True)
    faculty_recruiter_id = models.UUIDField(db_index=True)
    
    claim_reason = models.CharField(max_length=50, choices=PlacementClaimReason.choices)
    incident_date = models.DateField()
    claim_description = models.TextField()
    
    status = models.CharField(
        max_length=50,
        choices=PlacementClaimStatus.choices,
        default=PlacementClaimStatus.SUBMITTED,
        db_index=True,
    )
    
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_id = models.UUIDField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    refund_status = models.CharField(max_length=50, null=True, blank=True)
    refund_reference = models.CharField(max_length=200, null=True, blank=True)
    
    supporting_documents = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "billing_placement_claim"
        constraints = [
            models.UniqueConstraint(
                fields=["application"],
                condition=models.Q(is_deleted=False)
                & ~models.Q(status__in=(PlacementClaimStatus.REJECTED, PlacementClaimStatus.CLOSED, PlacementClaimStatus.REFUND_FAILED)),
                name="unique_active_placement_claim",
            ),
        ]

    def __str__(self):
        return self.claim_number


class PlacementClaimHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    claim = models.ForeignKey(
        PlacementClaim, on_delete=models.CASCADE, related_name="history"
    )
    from_status = models.CharField(
        max_length=50, choices=PlacementClaimStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=50, choices=PlacementClaimStatus.choices)
    changed_by_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "billing_placement_claim_history"
        ordering = ["-changed_at"]
