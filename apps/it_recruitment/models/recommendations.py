"""Persisted job recommendation cache for job seekers."""

from django.db import models

from apps.core.models.base import AuditedBaseModel
from apps.it_recruitment.models.profiles import JobSeekerProfile
from apps.jobs.models import JobPosting


class JobSeekerRecommendationSnapshot(AuditedBaseModel):
    """Aggregate metadata for a seeker's latest recommendation computation."""

    job_seeker = models.OneToOneField(
        JobSeekerProfile,
        on_delete=models.CASCADE,
        related_name="recommendation_snapshot",
    )
    total_matches = models.PositiveIntegerField(default=0)
    new_matches_count = models.PositiveIntegerField(default=0)
    top_match_score = models.PositiveSmallIntegerField(default=0)
    top_match_job = models.ForeignKey(
        JobPosting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    profile_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    computed_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "it_job_seeker_recommendation_snapshot"


class JobSeekerJobRecommendation(AuditedBaseModel):
    """Cached match score for a single job–seeker pair."""

    job_seeker = models.ForeignKey(
        JobSeekerProfile,
        on_delete=models.CASCADE,
        related_name="job_recommendations",
    )
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="seeker_recommendations",
    )
    match_score = models.PositiveSmallIntegerField()
    score_breakdown = models.JSONField(default=dict, blank=True)
    rank = models.PositiveIntegerField(default=0)
    profile_fingerprint = models.CharField(max_length=64, blank=True)
    computed_at = models.DateTimeField()
    is_new = models.BooleanField(default=False)

    class Meta:
        db_table = "it_job_seeker_job_recommendation"
        constraints = [
            models.UniqueConstraint(
                fields=["job_seeker", "job_posting"],
                name="uniq_seeker_job_recommendation",
            ),
        ]
        indexes = [
            models.Index(fields=["job_seeker", "rank"]),
            models.Index(fields=["job_seeker", "-match_score"]),
            models.Index(fields=["job_posting"]),
        ]
        ordering = ["rank"]

    def __str__(self) -> str:
        return f"{self.job_seeker_id} → {self.job_posting_id} ({self.match_score}%)"
