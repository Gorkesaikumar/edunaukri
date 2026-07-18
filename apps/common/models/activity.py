"""Public "Live Hiring Activity" event stream.

A lightweight, append-only feed of recruitment activity across both domains
(IT + Faculty) used purely for public social proof on the landing page.
Rows are typically written by domain services when meaningful events occur
(job posted, candidate hired, recruiter verified, organization joined, ...).
"""

from django.db import models

from apps.common.constants.enums import ActivityDomain, ActivityType
from apps.core.models.base import BaseModel
from apps.documents.models import StoredFile


class PlatformActivity(BaseModel):
    org_name = models.CharField(max_length=200)
    domain = models.CharField(
        max_length=20,
        choices=ActivityDomain.choices,
        default=ActivityDomain.IT,
        db_index=True,
    )
    activity_type = models.CharField(
        max_length=30, choices=ActivityType.choices, db_index=True
    )
    # Action text shown after the org name, e.g. "posted Senior Java Developer".
    headline = models.CharField(max_length=255)
    logo_file = models.ForeignKey(
        StoredFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logos",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "common_platform_activity"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "created_at"]),
        ]

    def __str__(self):
        return f"{self.org_name} {self.headline}"
