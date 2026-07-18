from django.db import models
from django.utils import timezone


class SessionRevocation(models.Model):
    """Tracks when an admin force-logs-out a user; JWTs issued before this time are rejected."""

    domain = models.CharField(max_length=20, db_index=True)
    user_id = models.UUIDField(db_index=True)
    revoked_at = models.DateTimeField(default=timezone.now)
    revoked_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "auth_session_revocation"
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "user_id"], name="uniq_session_revocation_domain_user"
            ),
        ]
