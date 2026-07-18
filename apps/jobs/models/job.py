from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.core.validators import MinValueValidator

from apps.core.validators.common import validate_clean_text, validate_organization_name
from apps.companies.models import Company
from apps.core.models.base import AuditedBaseModel
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.jobs.constants.enums import (
    EmploymentType,
    JobStatus,
    JobVisibility,
    SalaryVisibility,
    WorkMode,
)
from apps.jobs.managers import JobPostingManager


class Skill(AuditedBaseModel):
    name = models.CharField(max_length=100, unique=True, validators=[validate_clean_text])
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "it_skill"

    def __str__(self):
        return self.name


class JobPosting(AuditedBaseModel):
    # Backward-compatible aliases (legacy code references JobPosting.EmploymentType / JobStatus).
    EmploymentType = EmploymentType
    JobStatus = JobStatus
    WorkMode = WorkMode

    # Relationships
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="job_postings"
    )
    posted_by = models.ForeignKey(
        RecruiterProfile, on_delete=models.PROTECT, related_name="job_postings"
    )

    # Identity
    title = models.CharField(max_length=300, validators=[validate_clean_text])
    slug = models.SlugField(max_length=350)
    job_code = models.CharField(max_length=50, blank=True, db_index=True)
    category = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)

    # Descriptive content
    description = models.TextField(validators=[validate_clean_text])
    requirements = models.TextField(blank=True, validators=[validate_clean_text])
    roles_responsibilities = models.TextField(blank=True, validators=[validate_clean_text])
    benefits = models.TextField(blank=True, validators=[validate_clean_text])
    education_requirement = models.CharField(max_length=255, blank=True)

    # Classification
    employment_type = models.CharField(
        max_length=50, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    work_mode = models.CharField(
        max_length=20, choices=WorkMode.choices, default=WorkMode.ONSITE
    )

    # Experience
    experience_min = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    experience_max = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    # Compensation
    salary_min = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    salary_max = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    salary_currency = models.CharField(max_length=3, default="INR")
    salary_visibility = models.CharField(
        max_length=20,
        choices=SalaryVisibility.choices,
        default=SalaryVisibility.VISIBLE,
    )

    # Capacity & timeline
    vacancies = models.PositiveIntegerField(default=1)
    joining_timeline = models.CharField(max_length=150, blank=True)
    application_deadline = models.DateTimeField(null=True, blank=True)

    # Ownership metadata
    hiring_manager = models.CharField(max_length=200, blank=True)

    # Primary location (structured)
    country = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    office_address = models.CharField(max_length=500, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_remote = models.BooleanField(default=False)

    # Flags & visibility
    visibility = models.CharField(
        max_length=20, choices=JobVisibility.choices, default=JobVisibility.PUBLIC
    )
    is_featured = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    is_template = models.BooleanField(default=False)

    # Lifecycle
    status = models.CharField(
        max_length=20, choices=JobStatus.choices, default=JobStatus.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Snapshots & counters
    company_name_snapshot = models.CharField(max_length=300)
    application_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    objects = JobPostingManager()

    class Meta:
        db_table = "it_job_posting"
        default_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "slug"], name="unique_company_job_slug"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "is_featured"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["published_at"]),
            GinIndex(fields=["title"], name="job_title_gin", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["company_name_snapshot"], name="job_comp_gin", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["location"], name="job_loc_gin", opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_published(self) -> bool:
        return self.status == JobStatus.PUBLISHED

    @property
    def is_draft(self) -> bool:
        return self.status == JobStatus.DRAFT

    @property
    def accepts_applications(self) -> bool:
        return self.status == JobStatus.PUBLISHED


class JobLocation(AuditedBaseModel):
    """Additional locations supporting multi-location job postings."""

    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="locations"
    )
    country = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    office_address = models.CharField(max_length=500, blank=True)
    work_mode = models.CharField(
        max_length=20, choices=WorkMode.choices, default=WorkMode.ONSITE
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "it_job_location"

    def __str__(self):
        return f"{self.city or self.country} ({self.job_posting_id})"


class JobPostingSkill(AuditedBaseModel):
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="required_skills"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.PROTECT, related_name="job_postings"
    )
    is_preferred = models.BooleanField(default=False)

    class Meta:
        db_table = "it_job_posting_skill"
        constraints = [
            models.UniqueConstraint(
                fields=["job_posting", "skill"], name="unique_job_skill"
            ),
        ]


class JobSeekerSkill(AuditedBaseModel):
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="skills"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.PROTECT, related_name="job_seekers"
    )
    proficiency_level = models.PositiveSmallIntegerField(default=3)
    years_of_experience = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "it_job_seeker_skill"
        constraints = [
            models.UniqueConstraint(
                fields=["job_seeker", "skill"], name="unique_seeker_skill"
            ),
        ]


class SavedJob(AuditedBaseModel):
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="saved_jobs"
    )
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="saved_by"
    )

    class Meta:
        db_table = "it_saved_job"
        constraints = [
            models.UniqueConstraint(
                fields=["job_seeker", "job_posting"], name="unique_saved_job"
            ),
        ]
