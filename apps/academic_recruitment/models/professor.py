from django.db import models
from django.core.validators import MinValueValidator

from apps.core.validators.common import validate_clean_text, validate_phone, validate_organization_name
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileStatus, ProfileVisibility
from apps.accounts.profiles.managers import ProfileManager
from apps.colleges.models import Department
from apps.core.models.base import AuditedBaseModel
from apps.documents.models import StoredFile


class ProfessorModerationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    FLAGGED = "flagged", "Flagged"


class ProfessorProfile(AuditedBaseModel):
    user = models.OneToOneField(
        ProfessorUser, on_delete=models.CASCADE, related_name="professor_profile"
    )
    first_name = models.CharField(max_length=100, validators=[validate_clean_text])
    last_name = models.CharField(max_length=100, validators=[validate_clean_text])
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    highest_qualification = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    research_interests = models.TextField(blank=True, validators=[validate_clean_text])
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    teaching_experience_years = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    industry_experience_years = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    publications_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    current_designation = models.CharField(max_length=150, blank=True, validators=[validate_clean_text])
    current_institution = models.CharField(max_length=300, blank=True, validators=[validate_organization_name])
    expected_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    preferred_locations = models.JSONField(default=list, blank=True)
    profile_photo = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professor_photos",
    )
    cv_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professor_cvs",
    )
    profile_completeness = models.PositiveSmallIntegerField(default=0)
    profile_completed = models.BooleanField(default=False)
    profile_completed_at = models.DateTimeField(null=True, blank=True)
    completion_animation_shown = models.BooleanField(default=False)
    profile_completion_fingerprint = models.CharField(
        max_length=64, blank=True, default=""
    )
    moderation_status = models.CharField(
        max_length=20,
        choices=ProfessorModerationStatus.choices,
        default=ProfessorModerationStatus.PENDING,
        db_index=True,
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
        db_table = "faculty_professor_profile"
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    profile_completeness__gte=0, profile_completeness__lte=100
                ),
                name="professor_profile_completeness_range",
            ),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Qualification(AuditedBaseModel):
    name = models.CharField(max_length=200, unique=True)
    level = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "faculty_qualification"

    def __str__(self):
        return self.name


class ProfessorQualification(AuditedBaseModel):
    professor = models.ForeignKey(
        ProfessorProfile, on_delete=models.CASCADE, related_name="qualifications"
    )
    qualification = models.ForeignKey(
        Qualification, on_delete=models.PROTECT, related_name="professors"
    )
    institution_name = models.CharField(max_length=300, blank=True)
    year_obtained = models.PositiveSmallIntegerField(null=True, blank=True)
    certificate_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professor_certificates",
    )

    class Meta:
        db_table = "faculty_professor_qualification"


class ProfessorCertification(AuditedBaseModel):
    """Professional certifications uploaded by faculty job seekers."""

    professor = models.ForeignKey(
        ProfessorProfile, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=300)
    issuing_organization = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=30, default="other", db_index=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True)
    certificate_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professor_certifications",
    )
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "faculty_professor_certification"
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["professor", "category"]),
            models.Index(fields=["expiry_date"]),
        ]


class ProfessorDepartment(AuditedBaseModel):
    professor = models.ForeignKey(
        ProfessorProfile, on_delete=models.CASCADE, related_name="departments"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="professors"
    )

    class Meta:
        db_table = "faculty_professor_department"
        constraints = [
            models.UniqueConstraint(
                fields=["professor", "department"], name="unique_professor_department"
            ),
        ]
