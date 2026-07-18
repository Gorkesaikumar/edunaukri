from django.db import models
from django.utils import timezone

from apps.core.models.base import BaseModel
from apps.notifications.constants.enums import NotificationChannel, NotificationStatus


class Notification(BaseModel):
    recipient_domain = models.CharField(max_length=20, db_index=True)
    recipient_id = models.UUIDField(db_index=True)
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
    )
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    event_type = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient_domain", "recipient_id", "-created_at"],
                name="notif_recipient_idx",
            ),
        ]

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])
