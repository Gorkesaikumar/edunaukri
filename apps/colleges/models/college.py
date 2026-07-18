from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.profiles.constants.enums import ProfileStatus, ProfileVisibility
from apps.accounts.profiles.managers import ProfileManager
from apps.colleges.constants.enums import (
    CollegeMemberRole,
    InstitutionDocumentType,
    InstitutionType,
    OwnershipType,
)
from apps.colleges.managers import InstitutionManager
from apps.core.models.base import AuditedBaseModel
from apps.documents.models import StoredFile
from apps.core.validators.common import validate_organization_name, validate_clean_text, validate_phone


class Department(AuditedBaseModel):
    name = models.CharField(max_length=200, unique=True, validators=[validate_organization_name])
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "faculty_department"

    def __str__(self):
        return self.name


class College(AuditedBaseModel):
    # Identity
    name = models.CharField(max_length=300, validators=[validate_organization_name])
    legal_name = models.CharField(max_length=300, blank=True, validators=[validate_organization_name])
    slug = models.SlugField(max_length=320, unique=True)

    # Classification
    college_type = models.CharField(max_length=50, blank=True)
    institution_type = models.CharField(
        max_length=30, choices=InstitutionType.choices, blank=True
    )
    ownership_type = models.CharField(
        max_length=30, choices=OwnershipType.choices, blank=True
    )
    autonomous_status = models.BooleanField(default=False)

    # Narrative
    description = models.TextField(blank=True, validators=[validate_clean_text])
    vision = models.TextField(blank=True, validators=[validate_clean_text])
    mission = models.TextField(blank=True, validators=[validate_clean_text])
    infrastructure_description = models.TextField(blank=True, validators=[validate_clean_text])
    facilities = models.TextField(blank=True, validators=[validate_clean_text])
    placement_cell_details = models.TextField(blank=True, validators=[validate_clean_text])
    research_centers = models.TextField(blank=True, validators=[validate_clean_text])
    hostel_availability = models.BooleanField(default=False)
    transportation_facilities = models.BooleanField(default=False)

    # Academic structure
    affiliated_university = models.CharField(max_length=300, blank=True, validators=[validate_organization_name])
    academic_calendar_reference = models.CharField(max_length=500, blank=True)
    programs_offered = models.JSONField(default=list, blank=True)
    courses_offered = models.JSONField(default=list, blank=True)

    # Accreditation & approvals
    accreditation = models.CharField(max_length=100, blank=True)
    aicte_code = models.CharField(max_length=100, blank=True)
    ugc_code = models.CharField(max_length=100, blank=True)
    naac_grade = models.CharField(max_length=10, blank=True)
    nba_accreditation = models.CharField(max_length=200, blank=True)

    # Metrics
    established_year = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1800)])
    campus_area = models.CharField(max_length=100, blank=True)
    number_of_students = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    number_of_faculty = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    # Contact
    website_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    alternate_phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])

    # Branding
    logo_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="college_logos",
    )
    cover_banner_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="college_banners",
    )

    # Primary address (main campus)
    address_line = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=120, blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Social links
    linkedin_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    # Lifecycle
    is_active = models.BooleanField(default=True, db_index=True)

    profile_status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
        db_index=True,
    )
    profile_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        db_index=True,
    )

    # Profile Completion tracking
    profile_completeness = models.PositiveSmallIntegerField(default=0)
    profile_completed = models.BooleanField(default=False)
    completion_animation_shown = models.BooleanField(default=False)
    profile_completed_at = models.DateTimeField(null=True, blank=True)
    profile_completion_fingerprint = models.CharField(max_length=64, blank=True)

    objects = InstitutionManager()
    profiles = ProfileManager()

    class Meta:
        db_table = "faculty_college"
        default_manager_name = "objects"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:320]
        super().save(*args, **kwargs)

    @property
    def is_verified(self) -> bool:
        return self.is_active

    @property
    def can_publish_vacancies(self) -> bool:
        return self.is_active


class CollegeDepartment(AuditedBaseModel):
    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="departments"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="colleges"
    )

    class Meta:
        db_table = "faculty_college_department"
        constraints = [
            models.UniqueConstraint(
                fields=["college", "department"], name="unique_college_department"
            ),
        ]


class CollegeMember(AuditedBaseModel):
    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="members"
    )
    college_user = models.ForeignKey(
        CollegeUser, on_delete=models.CASCADE, related_name="college_memberships"
    )
    role = models.CharField(
        max_length=50,
        choices=CollegeMemberRole.choices,
        default=CollegeMemberRole.ADMIN,
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "faculty_college_member"
        constraints = [
            models.UniqueConstraint(
                fields=["college", "college_user"], name="unique_college_user_member"
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def __str__(self):
        return f"{self.college_user_id} @ {self.college_id}"


class InstitutionCampus(AuditedBaseModel):
    """Additional campuses supporting multi-campus institutions."""

    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="campuses"
    )
    label = models.CharField(max_length=150, blank=True)
    address_line = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=120, blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_main_campus = models.BooleanField(default=False)

    class Meta:
        db_table = "faculty_college_campus"

    def __str__(self):
        return f"{self.label or self.city} ({self.college_id})"


class InstitutionDocument(AuditedBaseModel):
    """Approval / accreditation / branding documents attached to an institution."""

    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=40, choices=InstitutionDocumentType.choices
    )
    stored_file = models.ForeignKey(
        StoredFile, on_delete=models.PROTECT, related_name="institution_documents"
    )
    title = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "faculty_college_document"

    def __str__(self):
        return f"{self.document_type} ({self.college_id})"
