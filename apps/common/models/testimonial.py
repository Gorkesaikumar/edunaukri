"""Placement success-story testimonial (public marketing content).

Database-driven testimonials shown in the landing page "Success Stories"
carousel. Covers both recruitment domains (IT and Faculty). Only rows that
are approved, active, public, and verified are surfaced publicly.
"""

from django.db import models

from apps.common.constants.enums import (
    TestimonialDomain,
    TestimonialVisibility,
)
from apps.core.models.base import AuditedBaseModel
from apps.documents.models import StoredFile


class Testimonial(AuditedBaseModel):
    # Author identity
    author_name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, blank=True)
    organization_name = models.CharField(max_length=200, blank=True)
    photo_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="testimonial_photos",
    )

    # Classification
    domain = models.CharField(
        max_length=20,
        choices=TestimonialDomain.choices,
        default=TestimonialDomain.IT,
        db_index=True,
    )

    # Content
    rating = models.PositiveSmallIntegerField(default=5)
    quote = models.TextField()

    # Success metrics (power the professional badges + "Highest Salary" sort)
    days_to_hire = models.PositiveSmallIntegerField(null=True, blank=True)
    salary_increase_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    joined_dream_company = models.BooleanField(default=False)

    # Lifecycle / moderation
    is_verified = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    visibility = models.CharField(
        max_length=20,
        choices=TestimonialVisibility.choices,
        default=TestimonialVisibility.PUBLIC,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "common_testimonial"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "visibility"]),
            models.Index(fields=["domain", "is_verified"]),
        ]

    def __str__(self):
        return f"{self.author_name} ({self.organization_name})"
