from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator

from apps.core.validators.common import (
    validate_organization_name,
    validate_gst,
    validate_phone,
    validate_clean_text,
)
from apps.companies.constants.enums import (
    CompanyMemberRole,
    CompanySize,
    OrganizationType,
)
from apps.companies.managers import CompanyManager
from apps.core.models.base import AuditedBaseModel
from apps.documents.models import StoredFile
from apps.it_recruitment.models import RecruiterProfile


class Company(AuditedBaseModel):
    # Identity
    name = models.CharField(max_length=300, validators=[validate_organization_name])
    legal_name = models.CharField(max_length=300, blank=True, validators=[validate_organization_name])
    slug = models.SlugField(max_length=320, unique=True)

    # Profile / narrative
    description = models.TextField(blank=True, validators=[validate_clean_text])
    mission = models.TextField(blank=True, validators=[validate_clean_text])
    vision = models.TextField(blank=True, validators=[validate_clean_text])
    benefits = models.TextField(blank=True, validators=[validate_clean_text])
    culture = models.TextField(blank=True, validators=[validate_clean_text])

    # Classification
    industry = models.CharField(max_length=100, blank=True)
    organization_type = models.CharField(
        max_length=30, choices=OrganizationType.choices, blank=True
    )
    company_size = models.CharField(
        max_length=20, choices=CompanySize.choices, blank=True
    )
    founded_year = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1800)])
    gst_number = models.CharField(max_length=20, blank=True, validators=[validate_gst])

    # Contact
    website_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])

    # Branding
    logo_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_logos",
    )
    cover_banner_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_banners",
    )

    # Primary address
    headquarters_location = models.CharField(max_length=200, blank=True)
    address_line = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Social links
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    # Lifecycle
    is_active = models.BooleanField(default=True, db_index=True)

    objects = CompanyManager()

    class Meta:
        db_table = "it_company"
        verbose_name_plural = "companies"

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
    def can_publish_jobs(self) -> bool:
        return self.is_active


class CompanyMember(AuditedBaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="members"
    )
    recruiter = models.ForeignKey(
        RecruiterProfile, on_delete=models.CASCADE, related_name="company_memberships"
    )
    role = models.CharField(
        max_length=50,
        choices=CompanyMemberRole.choices,
        default=CompanyMemberRole.RECRUITER,
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "it_company_member"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "recruiter"], name="unique_company_recruiter"
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def __str__(self):
        return f"{self.recruiter_id} @ {self.company_id}"


class CompanyLocation(AuditedBaseModel):
    """Additional office locations beyond the primary/headquarters address."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="locations"
    )
    label = models.CharField(max_length=120, blank=True)
    address_line = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    is_headquarters = models.BooleanField(default=False)

    class Meta:
        db_table = "it_company_location"

    def __str__(self):
        return f"{self.label or self.city} ({self.company_id})"
