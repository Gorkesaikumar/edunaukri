from django.db import models

from apps.core.constants.enums import RecordStatus


class StatusModel(models.Model):
    """Abstract model with a canonical lifecycle status field."""

    status = models.CharField(
        max_length=30,
        choices=RecordStatus.choices,
        default=RecordStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        abstract = True

    @property
    def is_active_record(self) -> bool:
        return self.status == RecordStatus.ACTIVE
