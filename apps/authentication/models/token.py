import hashlib
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models.base import BaseModel


class AuthTokenPurpose(models.TextChoices):
    PASSWORD_RESET = "password_reset", "Password Reset"
    EMAIL_VERIFICATION = "email_verification", "Email Verification"


class AuthToken(BaseModel):
    """Single-use token for password reset and email verification."""

    domain = models.CharField(max_length=20, db_index=True)
    user_id = models.UUIDField(db_index=True)
    email = models.EmailField()
    purpose = models.CharField(
        max_length=30, choices=AuthTokenPurpose.choices, db_index=True
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_token"
        indexes = [
            models.Index(fields=["domain", "user_id", "purpose"]),
        ]

    @classmethod
    def generate(cls) -> tuple[str, str]:
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw, token_hash

    @classmethod
    def hash_token(cls, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    @property
    def is_valid(self) -> bool:
        return (
            self.used_at is None
            and self.expires_at > timezone.now()
            and not self.is_deleted
        )

    @classmethod
    def default_expiry(cls, hours: int = 24):
        return timezone.now() + timedelta(hours=hours)
