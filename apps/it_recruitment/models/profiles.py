from django.db import models
from django.core.validators import MinValueValidator

from apps.core.validators.common import validate_phone, validate_organization_name, validate_clean_text
from apps.accounts.models.it_user import ITUser
from apps.accounts.profiles.constants.enums import (
    EmploymentTypePreference,
    Gender,
    ProfileStatus,
    ProfileVisibility,
    WorkModePreference,
)
from apps.accounts.profiles.managers import ProfileManager
from apps.core.models.base import AuditedBaseModel
from apps.documents.models import StoredFile
from apps.it_recruitment.constants.education_enums import (
    EducationBoard,
    EducationLevel,
    EducationScoreType,
    IntermediateStream,
)
from apps.jobs.constants.enums import EmploymentType


class JobSeekerProfile(AuditedBaseModel):
    user = models.OneToOneField(
        ITUser, on_delete=models.CASCADE, related_name="job_seeker_profile"
    )
    first_name = models.CharField(max_length=100, validators=[validate_clean_text])
    last_name = models.CharField(max_length=100, validators=[validate_clean_text])
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    gender = models.CharField(max_length=30, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="India")
    headline = models.CharField(max_length=300, blank=True, validators=[validate_clean_text])
    summary = models.TextField(blank=True, validators=[validate_clean_text])
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    current_location = models.CharField(max_length=200, blank=True)
    preferred_location = models.CharField(max_length=200, blank=True)
    current_company = models.CharField(max_length=200, blank=True, validators=[validate_organization_name])
    current_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    expected_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    notice_period_days = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    employment_type_preference = models.CharField(
        max_length=50, choices=EmploymentTypePreference.choices, blank=True
    )
    work_mode_preference = models.CharField(
        max_length=20, choices=WorkModePreference.choices, blank=True
    )
    preferred_roles = models.JSONField(default=list, blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    personal_website = models.URLField(blank=True)
    languages = models.JSONField(default=list, blank=True)
    profile_photo = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_seeker_photos",
    )
    resume_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_seeker_resumes",
    )
    profile_completeness = models.PositiveSmallIntegerField(default=0)
    profile_completed = models.BooleanField(default=False, db_index=True)
    completion_animation_shown = models.BooleanField(default=False)
    profile_completed_at = models.DateTimeField(null=True, blank=True)
    profile_completion_fingerprint = models.CharField(max_length=64, blank=True)
    profile_status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
        db_index=True,
    )
    profile_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PRIVATE,
        db_index=True,
    )

    profiles = ProfileManager()

    class Meta:
        db_table = "it_job_seeker_profile"
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    profile_completeness__gte=0, profile_completeness__lte=100
                ),
                name="job_seeker_profile_completeness_range",
            ),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class RecruiterProfile(AuditedBaseModel):
    user = models.OneToOneField(
        ITUser, on_delete=models.CASCADE, related_name="recruiter_profile"
    )
    first_name = models.CharField(max_length=100, validators=[validate_clean_text])
    last_name = models.CharField(max_length=100, validators=[validate_clean_text])
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    official_email = models.EmailField(blank=True)
    designation = models.CharField(max_length=150, blank=True, validators=[validate_clean_text])
    department = models.CharField(max_length=150, blank=True, validators=[validate_clean_text])
    company_association = models.CharField(max_length=300, blank=True, validators=[validate_organization_name])
    profile_image = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recruiter_photos",
    )
    profile_status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
        db_index=True,
    )
    profile_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PRIVATE,
        db_index=True,
    )

    profiles = ProfileManager()

    class Meta:
        db_table = "it_recruiter_profile"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class JobSeekerExperience(AuditedBaseModel):
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="experiences"
    )
    company_name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        blank=True,
        default=EmploymentType.FULL_TIME,
    )
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "it_job_seeker_experience"
        ordering = ["-start_date", "-created_at"]


class JobSeekerEducation(AuditedBaseModel):
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="education"
    )
    education_level = models.CharField(
        max_length=30,
        choices=EducationLevel.choices,
        default=EducationLevel.DEGREE,
        db_index=True,
    )
    institution = models.CharField(max_length=300)
    university = models.CharField(max_length=300, blank=True)
    college = models.CharField(max_length=300, blank=True)
    board = models.CharField(max_length=50, choices=EducationBoard.choices, blank=True)
    stream = models.CharField(
        max_length=50, choices=IntermediateStream.choices, blank=True
    )
    degree_type = models.CharField(max_length=50, blank=True)
    score_type = models.CharField(
        max_length=20, choices=EducationScoreType.choices, blank=True
    )
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    passing_year = models.PositiveSmallIntegerField(null=True, blank=True)
    start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "it_job_seeker_education"
        ordering = ["education_level", "-end_year", "-passing_year", "-start_year"]

    @property
    def level_label(self) -> str:
        return (
            EducationLevel(self.education_level).label
            if self.education_level
            else "Education"
        )

    @property
    def score_display(self) -> str:
        if (
            self.score_type == EducationScoreType.PERCENTAGE
            and self.percentage is not None
        ):
            return f"{self.percentage}%"
        if self.score_type == EducationScoreType.CGPA and self.cgpa is not None:
            return f"CGPA {self.cgpa}"
        if self.percentage is not None:
            return f"{self.percentage}%"
        if self.cgpa is not None:
            return f"CGPA {self.cgpa}"
        return ""

    @property
    def year_display(self) -> str:
        if self.education_level in (EducationLevel.SCHOOL, EducationLevel.INTERMEDIATE):
            year = self.passing_year or self.end_year
            return str(year) if year else ""
        if self.start_year and self.end_year:
            return f"{self.start_year} – {self.end_year}"
        if self.end_year:
            return str(self.end_year)
        if self.start_year:
            return str(self.start_year)
        return ""


class JobSeekerProject(AuditedBaseModel):
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    technologies = models.JSONField(default=list, blank=True)
    project_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    class Meta:
        db_table = "it_job_seeker_project"
        ordering = ["-created_at"]


class JobSeekerCertification(AuditedBaseModel):
    job_seeker = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=300)
    issuing_organization = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=30, default="other", db_index=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True)
    certificate_file = models.ForeignKey(
        "documents.StoredFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_seeker_certifications",
    )
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "it_job_seeker_certification"
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["job_seeker", "category"]),
            models.Index(fields=["expiry_date"]),
        ]
