from django.db import models


class OwnershipModel(models.Model):
    """Abstract ownership columns for resources scoped to a user or organization."""

    owner_type = models.CharField(max_length=50, db_index=True)
    owner_id = models.UUIDField(db_index=True)
    created_by_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["owner_type", "owner_id"], name="%(class)s_owner_idx"),
        ]
