from django.db import models
from django.utils import timezone

from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.models.base import AuditedBaseModel
from apps.guarantee_claims.constants.enums import (
    ClaimResolution,
    ClaimStatus,
    ClaimType,
    DEFAULT_GUARANTEE_DAYS,
    GuaranteeStatus,
)


class PlacementGuarantee(AuditedBaseModel):
    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    invoice_id = models.UUIDField(db_index=True)
    placement_fee_id = models.UUIDField(null=True, blank=True, db_index=True)
    application_entity_type = models.CharField(
        max_length=40, choices=EntityReferenceType.choices
    )
    application_entity_id = models.UUIDField(db_index=True)
    guarantee_days = models.PositiveIntegerField(default=DEFAULT_GUARANTEE_DAYS)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=GuaranteeStatus.choices,
        default=GuaranteeStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        db_table = "billing_placement_guarantee"
        constraints = [
            models.UniqueConstraint(
                fields=["invoice_id"],
                condition=models.Q(is_deleted=False),
                name="unique_active_guarantee_per_invoice",
            ),
        ]

    def __str__(self):
        return f"Guarantee {self.invoice_id} ({self.status})"


class GuaranteeClaim(AuditedBaseModel):
    claim_number = models.CharField(max_length=50, unique=True)
    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    
    recruiter_id = models.UUIDField(null=True, blank=True, db_index=True)
    institution_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    guarantee_id = models.UUIDField(null=True, blank=True, db_index=True)
    application_entity_type = models.CharField(
        max_length=40, choices=EntityReferenceType.choices
    )
    application_entity_id = models.UUIDField(db_index=True)
    placement_fee_id = models.UUIDField(null=True, blank=True, db_index=True)
    invoice_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Dates
    joining_date = models.DateField(null=True, blank=True)
    guarantee_start_date = models.DateField(null=True, blank=True)
    guarantee_end_date = models.DateField(null=True, blank=True)
    exit_date = models.DateField(null=True, blank=True)
    
    from apps.guarantee_claims.constants.enums import ExitReason
    exit_reason = models.CharField(max_length=50, choices=ExitReason.choices, blank=True)
    claim_type = models.CharField(max_length=20, choices=ClaimType.choices)
    
    status = models.CharField(
        max_length=30,
        choices=ClaimStatus.choices,
        default=ClaimStatus.SUBMITTED,
        db_index=True,
    )
    resolution = models.CharField(
        max_length=30, choices=ClaimResolution.choices, blank=True
    )
    
    reason = models.TextField()
    claim_description = models.TextField(blank=True)
    
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    approved_by_id = models.UUIDField(null=True, blank=True)
    
    admin_notes = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    replacement_status = models.CharField(max_length=50, blank=True)
    
    supporting_documents = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "billing_guarantee_claim"
        constraints = [
            models.UniqueConstraint(
                fields=["invoice_id"],
                condition=models.Q(is_deleted=False)
                & ~models.Q(status__in=(ClaimStatus.REJECTED, ClaimStatus.RESOLVED, ClaimStatus.CANCELLED)),
                name="unique_active_claim_per_invoice",
            ),
        ]

    def __str__(self):
        return self.claim_number

    @property
    def get_application(self):
        """Returns the actual application object (IT or Faculty)."""
        if not hasattr(self, '_resolved_application'):
            from apps.applications.models import JobApplication, FacultyApplication
            from apps.core.constants.enums import DomainType
            
            if self.domain == DomainType.IT:
                self._resolved_application = JobApplication.objects.filter(pk=self.application_entity_id).select_related('job_seeker', 'job_posting').first()
            elif self.domain == DomainType.FACULTY:
                self._resolved_application = FacultyApplication.objects.filter(pk=self.application_entity_id).select_related('professor', 'vacancy').first()
            else:
                self._resolved_application = None
                
        return self._resolved_application
        
    @property
    def candidate_name(self):
        app = self.get_application
        if not app: return "Unknown Candidate"
        
        from apps.core.constants.enums import DomainType
        if self.domain == DomainType.IT and hasattr(app, 'job_seeker'):
            return app.job_seeker.full_name
        elif self.domain == DomainType.FACULTY and hasattr(app, 'professor'):
            return f"{app.professor.first_name} {app.professor.last_name}".strip()
        return "Unknown Candidate"
        
    @property
    def job_title(self):
        app = self.get_application
        if not app: return "Unknown Role"
        
        from apps.core.constants.enums import DomainType
        if self.domain == DomainType.IT and hasattr(app, 'job_posting'):
            return app.job_posting.title
        elif self.domain == DomainType.FACULTY and hasattr(app, 'vacancy'):
            return app.vacancy.title
        return "Unknown Role"
        
    @property
    def recruiter_name(self):
        app = self.get_application
        if not app: return "Unknown Recruiter"
        
        from apps.core.constants.enums import DomainType
        if self.domain == DomainType.IT and hasattr(app, 'company'):
            return app.company.name if app.company else "Unknown Company"
        elif self.domain == DomainType.FACULTY:
            # Faculty doesn't have company on application directly sometimes, check institution
            from apps.colleges.models import College
            if self.institution_id:
                college = College.objects.filter(pk=self.institution_id).first()
                return college.name if college else "Unknown Institution"
            return "Unknown Institution"
        return "Unknown Recruiter"
        
    @property
    def candidate_profile_url(self):
        from django.urls import reverse, NoReverseMatch
        try:
            # We don't have user_uuid in the model context easily, so returning a hash 
            # or we could construct a path if we knew the super admin uuid.
            # Instead of failing silently to "#", let's return a safe placeholder
            # or rely on the frontend to inject it if needed.
            # Actually, since we can't reverse namespaced URLs without user_uuid here,
            # we should return None and let the template handle the routing.
            pass
        except NoReverseMatch:
            pass
        return None
        
    @property
    def recruiter_profile_url(self):
        return None



class GuaranteeClaimHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    claim = models.ForeignKey(
        GuaranteeClaim, on_delete=models.CASCADE, related_name="history"
    )
    from_status = models.CharField(
        max_length=50, choices=ClaimStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=50, choices=ClaimStatus.choices)
    changed_by_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "billing_guarantee_claim_history"
        ordering = ["-changed_at"]
