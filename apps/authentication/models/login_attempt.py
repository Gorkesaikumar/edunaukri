from django.db import models
from django.utils import timezone

from apps.core.models.base import BaseModel


class LoginAttemptResult(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILURE = "failure", "Failure"
    LOCKED = "locked", "Locked"


class LoginAttempt(BaseModel):
    """Immutable login attempt audit record."""

    domain = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    result = models.CharField(
        max_length=20, choices=LoginAttemptResult.choices, db_index=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    failure_reason = models.CharField(max_length=100, blank=True)
    attempted_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "auth_login_attempt"
        ordering = ["-attempted_at"]
