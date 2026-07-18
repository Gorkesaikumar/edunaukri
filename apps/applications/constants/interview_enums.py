"""Interview scheduling enums for IT job applications."""

from django.db import models


class InterviewStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    CONFIRMED = "confirmed", "Confirmed"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    RESCHEDULED = "rescheduled", "Rescheduled"


class InterviewMode(models.TextChoices):
    ONLINE = "online", "Online"
    OFFLINE = "offline", "Offline"
    PHONE = "phone", "Phone"


class InterviewRoundType(models.TextChoices):
    HR = "hr", "HR Round"
    TECHNICAL = "technical", "Technical Round"
    MANAGERIAL = "managerial", "Managerial Round"
    FINAL = "final", "Final Round"
    DEMO = "demo", "Demo Class"
    PANEL = "panel", "Panel Interview"
    OTHER = "other", "Other"
