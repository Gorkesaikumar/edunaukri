from django.db import models
from django.utils import timezone

from apps.applications.constants.interview_enums import (
    InterviewMode,
    InterviewRoundType,
    InterviewStatus,
)
from apps.applications.models.application import JobApplication
from apps.core.constants.enums import DomainType
from apps.core.models.base import AuditedBaseModel


class JobApplicationInterview(AuditedBaseModel):
    """Scheduled interview round for an IT job application."""

    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, related_name="interviews"
    )
    domain = models.CharField(
        max_length=20, choices=DomainType.choices, default=DomainType.IT
    )
    interview_id = models.CharField(max_length=64, blank=True, db_index=True)
    round_type = models.CharField(
        max_length=30,
        choices=InterviewRoundType.choices,
        default=InterviewRoundType.TECHNICAL,
    )
    round_label = models.CharField(max_length=120, blank=True)
    interview_type = models.CharField(max_length=120, default="Technical Interview")
    mode = models.CharField(
        max_length=20, choices=InterviewMode.choices, default=InterviewMode.ONLINE
    )
    scheduled_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    timezone_label = models.CharField(max_length=64, default="IST")
    meet_url = models.URLField(max_length=500, blank=True)
    location = models.CharField(max_length=300, blank=True)
    panel = models.JSONField(default=list, blank=True)
    instructions = models.TextField(blank=True)
    required_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=InterviewStatus.choices,
        default=InterviewStatus.SCHEDULED,
        db_index=True,
    )
    candidate_confirmed = models.BooleanField(default=False)
    candidate_confirmed_at = models.DateTimeField(null=True, blank=True)
    feedback = models.JSONField(default=dict, blank=True)
    feedback_shared = models.BooleanField(default=False)
    reminder_sent_at = models.JSONField(default=dict, blank=True)
    scheduled_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "it_job_application_interview"
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["application", "status"]),
            models.Index(fields=["scheduled_at", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.round_label or self.interview_type} — {self.application_id}"

    def mark_confirmed(self) -> None:
        self.candidate_confirmed = True
        self.candidate_confirmed_at = timezone.now()
        if self.status == InterviewStatus.SCHEDULED:
            self.status = InterviewStatus.CONFIRMED
        self.save(
            update_fields=[
                "candidate_confirmed",
                "candidate_confirmed_at",
                "status",
                "updated_at",
            ]
        )

    def to_metadata(self) -> dict:
        """Snapshot for timeline metadata and legacy portal consumers."""
        return {
            "interview_id": self.interview_id or str(self.pk),
            "interview_round": self.round_type,
            "round_label": self.round_label or self.get_round_type_display(),
            "interview_type": self.interview_type,
            "mode": self.get_mode_display(),
            "interview_mode": self.mode,
            "scheduled_at": self.scheduled_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "duration": f"{self.duration_minutes} min",
            "timezone": self.timezone_label,
            "meet_url": self.meet_url,
            "meeting_link": self.meet_url,
            "location": self.location,
            "panel_members": self.panel,
            "panel": self.panel,
            "instructions": self.instructions,
            "required_documents": self.required_documents,
            "confirmed": self.candidate_confirmed,
            "candidate_confirmed": self.candidate_confirmed,
            "cancelled": self.status == InterviewStatus.CANCELLED,
            "rescheduled": self.status == InterviewStatus.RESCHEDULED,
            "feedback": self.feedback,
            "feedback_shared": self.feedback_shared,
        }


class InterviewEvaluation(AuditedBaseModel):
    domain = models.CharField(max_length=20, choices=DomainType.choices)
    application_id = models.UUIDField(db_index=True)
    
    technical_rating = models.PositiveSmallIntegerField(default=3)
    communication_rating = models.PositiveSmallIntegerField(default=3)
    subject_knowledge = models.PositiveSmallIntegerField(default=3)
    teaching_skills = models.PositiveSmallIntegerField(null=True, blank=True)  # Faculty Domain
    industry_skills = models.PositiveSmallIntegerField(null=True, blank=True)   # IT Domain
    culture_fit = models.PositiveSmallIntegerField(default=3)
    overall_rating = models.PositiveSmallIntegerField(default=3)
    
    interview_notes = models.TextField(blank=True)
    recommendation = models.CharField(max_length=30)  # e.g., 'select', 'reject', 'hold'

    class Meta:
        db_table = "recruitment_interview_evaluation"

