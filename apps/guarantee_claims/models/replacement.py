from django.db import models
from django.utils import timezone
from apps.core.models.base import AuditedBaseModel
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.applications.models import FacultyApplication, JobApplication

class ReplacementStatus(models.TextChoices):
    SEARCH_ACTIVE = "search_active", "Search Active"
    CANDIDATE_IDENTIFIED = "candidate_identified", "Candidate Identified"
    CANDIDATE_SELECTED = "candidate_selected", "Candidate Selected"
    CANDIDATE_JOINED = "candidate_joined", "Candidate Joined"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"

class ReplacementCandidateWorkflow(AuditedBaseModel):
    workflow_number = models.CharField(max_length=50, unique=True)
    claim = models.OneToOneField(GuaranteeClaim, on_delete=models.PROTECT, related_name="replacement_workflow")
    
    # Original Placement Tracking
    original_faculty_application = models.ForeignKey(FacultyApplication, on_delete=models.PROTECT, related_name="original_replacements", null=True, blank=True)
    original_it_application = models.ForeignKey(JobApplication, on_delete=models.PROTECT, related_name="original_replacements", null=True, blank=True)
    
    # Replacement Placement Tracking
    replacement_faculty_application = models.ForeignKey(FacultyApplication, on_delete=models.PROTECT, related_name="fulfilled_replacements", null=True, blank=True)
    replacement_it_application = models.ForeignKey(JobApplication, on_delete=models.PROTECT, related_name="fulfilled_replacements", null=True, blank=True)
    
    status = models.CharField(
        max_length=30,
        choices=ReplacementStatus.choices,
        default=ReplacementStatus.SEARCH_ACTIVE,
        db_index=True
    )
    
    search_started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "billing_guarantee_replacement"
        ordering = ["-created_at"]

    def __str__(self):
        return self.workflow_number
