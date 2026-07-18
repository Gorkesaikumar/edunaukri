from django.db import models

from apps.core.constants.enums import ActorType, DomainType
from apps.core.models.mixins import UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, models.Model):
    """Immutable platform-wide audit log entry."""

    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=50, blank=True, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor_type = models.CharField(
        max_length=50, choices=ActorType.choices, db_index=True
    )
    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_event"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["domain", "event_type", "-occurred_at"],
                name="audit_domain_event_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.occurred_at}"
