"""User login sessions and security audit models."""

import uuid

from django.db import models
from django.utils import timezone

from apps.core.models.base import AuditedBaseModel, BaseModel


class OAuthProvider(models.TextChoices):
    GOOGLE = "google", "Google"
    LINKEDIN = "linkedin", "LinkedIn"


class UserLoginSession(AuditedBaseModel):
    """Track active authentication sessions per domain user."""

    domain = models.CharField(max_length=20, db_index=True)
    user_id = models.UUIDField(db_index=True)
    session_uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    session_key = models.CharField(max_length=64, unique=True, db_index=True)
    device_label = models.CharField(max_length=200, blank=True)
    browser = models.CharField(max_length=80, blank=True)
    os_name = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    location_label = models.CharField(max_length=120, blank=True)
    login_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_active_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_user_login_session"
        ordering = ["-last_active_at"]
        indexes = [
            models.Index(fields=["domain", "user_id", "-last_active_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and not self.is_deleted


class SecurityAuditEvent(BaseModel):
    """User-facing security activity log."""

    domain = models.CharField(max_length=20, db_index=True)
    user_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=60, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "auth_security_audit_event"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["domain", "user_id", "-occurred_at"]),
        ]


class ConnectedOAuthAccount(AuditedBaseModel):
    """Linked social login providers."""

    domain = models.CharField(max_length=20, db_index=True)
    user_id = models.UUIDField(db_index=True)
    provider = models.CharField(
        max_length=20, choices=OAuthProvider.choices, db_index=True
    )
    provider_user_id = models.CharField(max_length=200, blank=True)
    provider_email = models.EmailField(blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_connected_oauth_account"
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "user_id", "provider"],
                name="auth_oauth_unique_provider_per_user",
            ),
        ]

    @property
    def is_connected(self) -> bool:
        return (
            self.connected_at is not None
            and self.disconnected_at is None
            and not self.is_deleted
        )
