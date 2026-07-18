from django.db import models

from apps.core.constants.enums import DomainType
from apps.core.models.base import BaseModel


class OutboxEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class OutboxEvent(BaseModel):
    """Transactional outbox for Phase 2 async event processing."""

    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    aggregate_type = models.CharField(max_length=50)
    aggregate_id = models.UUIDField(db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=OutboxEventStatus.choices,
        default=OutboxEventStatus.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "core_outbox_event"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["status", "created_at"], name="core_outbox_pending_idx"
            ),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.status})"
