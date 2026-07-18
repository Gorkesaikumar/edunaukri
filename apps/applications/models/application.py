from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from apps.core.validators.common import validate_clean_text
from apps.companies.models import Company
from apps.core.constants.enums import DomainType
from apps.core.models.base import AuditedBaseModel
from apps.documents.models import StoredFile
from apps.it_recruitment.models import JobSeekerProfile
from apps.jobs.models import JobPosting
from apps.applications.constants.enums import (
    ApplicationSource,
    JobApplicationStatus,
    TimelineEventType,
)
from apps.applications.constants.faculty_enums import (
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)


class JobApplication(AuditedBaseModel):
    # Backward-compatible alias for legacy imports.
    ApplicationStatus = JobApplicationStatus

    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.PROTECT, related_name="applications"
    )
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.PROTECT, related_name="applications"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="job_applications",
        null=True,
        blank=True,
    )
    resume_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_applications",
    )
    resume_snapshot = models.JSONField(default=dict, blank=True)
    cover_letter = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=JobApplicationStatus.choices,
        default=JobApplicationStatus.APPLIED,
        db_index=True,
    )
    applied_at = models.DateTimeField(default=timezone.now, db_index=True)
    status_changed_at = models.DateTimeField(default=timezone.now)
    placed_at = models.DateTimeField(null=True, blank=True)
    hired_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    expected_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    notice_period = models.CharField(max_length=100, blank=True, validators=[validate_clean_text])
    current_location = models.CharField(max_length=200, blank=True)
    source = models.CharField(
        max_length=30,
        choices=ApplicationSource.choices,
        default=ApplicationSource.DIRECT,
        blank=True,
    )

    recruiter_notes = models.TextField(blank=True)
    candidate_notes = models.TextField(blank=True)
    internal_remarks = models.TextField(blank=True)

    applicant_name_snapshot = models.CharField(max_length=200)
    job_title_snapshot = models.CharField(max_length=300)
    company_name_snapshot = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "it_job_application"
        constraints = [
            models.UniqueConstraint(
                fields=["job_posting", "job_seeker"],
                condition=models.Q(is_deleted=False),
                name="unique_active_job_application",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "company"]),
            models.Index(fields=["job_posting", "status"]),
        ]

    @property
    def is_terminal(self) -> bool:
        from apps.applications.workflow.engine import ApplicationWorkflowEngine

        return ApplicationWorkflowEngine.is_terminal(self.status)


class JobApplicationStatusHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, related_name="status_history"
    )
    from_status = models.CharField(
        max_length=30, choices=JobApplicationStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=30, choices=JobApplicationStatus.choices)
    changed_by_id = models.UUIDField(null=True, blank=True)
    changed_by_domain = models.CharField(
        max_length=20, choices=DomainType.choices, default=DomainType.IT
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "it_application_status_history"
        ordering = ["-changed_at"]


class JobApplicationTimelineEvent(models.Model):
    """Rich application timeline beyond bare status history."""

    id = models.BigAutoField(primary_key=True)
    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, related_name="timeline"
    )
    event_type = models.CharField(
        max_length=30, choices=TimelineEventType.choices, db_index=True
    )
    from_status = models.CharField(
        max_length=30, choices=JobApplicationStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(
        max_length=30, choices=JobApplicationStatus.choices, null=True, blank=True
    )
    actor_id = models.UUIDField(null=True, blank=True)
    actor_domain = models.CharField(
        max_length=20, choices=DomainType.choices, default=DomainType.IT
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "it_application_timeline_event"
        ordering = ["-occurred_at"]


class FacultyApplication(AuditedBaseModel):
    # Backward-compatible alias for legacy imports.
    ApplicationStatus = FacultyApplicationStatus

    vacancy = models.ForeignKey(
        "faculty.FacultyVacancy", on_delete=models.PROTECT, related_name="applications"
    )
    professor = models.ForeignKey(
        "academic_recruitment.ProfessorProfile",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    college = models.ForeignKey(
        "colleges.College",
        on_delete=models.PROTECT,
        related_name="faculty_applications",
        null=True,
        blank=True,
    )
    cv_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_applications",
    )
    cv_snapshot = models.JSONField(default=dict, blank=True)
    qualification_snapshot = models.JSONField(default=list, blank=True)
    specialization_snapshot = models.JSONField(default=dict, blank=True)
    experience_snapshot = models.JSONField(default=dict, blank=True)
    certificates_snapshot = models.JSONField(default=list, blank=True)
    cover_letter = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=FacultyApplicationStatus.choices,
        default=FacultyApplicationStatus.APPLIED,
        db_index=True,
    )
    applied_at = models.DateTimeField(default=timezone.now, db_index=True)
    status_changed_at = models.DateTimeField(default=timezone.now)
    placed_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    department = models.CharField(max_length=200, blank=True)
    expected_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    current_institution = models.CharField(max_length=300, blank=True)
    current_designation = models.CharField(max_length=150, blank=True)
    research_publications_count = models.PositiveIntegerField(default=0)
    source = models.CharField(
        max_length=30,
        choices=ApplicationSource.choices,
        default=ApplicationSource.DIRECT,
        blank=True,
    )

    college_notes = models.TextField(blank=True)
    professor_notes = models.TextField(blank=True)
    internal_remarks = models.TextField(blank=True)
    college_rating = models.PositiveSmallIntegerField(null=True, blank=True)

    applicant_name_snapshot = models.CharField(max_length=200)
    vacancy_title_snapshot = models.CharField(max_length=300)
    college_name_snapshot = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "faculty_application"
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "professor"],
                condition=models.Q(is_deleted=False),
                name="unique_active_faculty_application",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "college"]),
            models.Index(fields=["vacancy", "status"]),
            models.Index(fields=["professor", "status"]),
        ]

    @property
    def is_terminal(self) -> bool:
        from apps.applications.workflow.faculty_engine import (
            FacultyApplicationWorkflowEngine,
        )

        return FacultyApplicationWorkflowEngine.is_terminal(self.status)


class FacultyApplicationStatusHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    application = models.ForeignKey(
        FacultyApplication, on_delete=models.CASCADE, related_name="status_history"
    )
    from_status = models.CharField(
        max_length=30, choices=FacultyApplicationStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(
        max_length=30, choices=FacultyApplicationStatus.choices
    )
    changed_by_id = models.UUIDField(null=True, blank=True)
    changed_by_domain = models.CharField(
        max_length=20, choices=DomainType.choices, default=DomainType.FACULTY
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "faculty_application_status_history"
        ordering = ["-changed_at"]


class FacultyApplicationTimelineEvent(models.Model):
    """Rich faculty application timeline beyond bare status history."""

    id = models.BigAutoField(primary_key=True)
    application = models.ForeignKey(
        FacultyApplication, on_delete=models.CASCADE, related_name="timeline"
    )
    event_type = models.CharField(
        max_length=30, choices=FacultyTimelineEventType.choices, db_index=True
    )
    from_status = models.CharField(
        max_length=30, choices=FacultyApplicationStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(
        max_length=30, choices=FacultyApplicationStatus.choices, null=True, blank=True
    )
    actor_id = models.UUIDField(null=True, blank=True)
    actor_domain = models.CharField(
        max_length=20, choices=DomainType.choices, default=DomainType.FACULTY
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "faculty_application_timeline_event"
        ordering = ["-occurred_at"]


class PlacementDetails(AuditedBaseModel):
    domain = models.CharField(max_length=20, choices=DomainType.choices)
    application_id = models.UUIDField(db_index=True)
    
    # Selection details
    selected_at = models.DateTimeField(default=timezone.now)
    selected_by_id = models.UUIDField(null=True, blank=True)
    
    # Joining progress details (JOINING_IN_PROGRESS)
    expected_joining_date = models.DateField(null=True, blank=True)
    offered_designation = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=200, blank=True)
    work_location = models.CharField(max_length=200, blank=True)
    employment_type = models.CharField(max_length=100, blank=True)  # e.g., Full-time, Contract
    agreed_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True) # CTC
    offer_reference_number = models.CharField(max_length=100, blank=True)
    joining_notes = models.TextField(blank=True)
    
    # Actual joining details (JOINED)
    actual_joining_date = models.DateField(null=True, blank=True)
    employee_id = models.CharField(max_length=100, blank=True) # Faculty/Employee ID
    joining_confirmed_notes = models.TextField(blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    joined_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "recruitment_placement_details"
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "application_id"],
                condition=models.Q(is_deleted=False),
                name="unique_placement_details_per_application",
            )
        ]

