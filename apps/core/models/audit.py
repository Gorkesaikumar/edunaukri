from django.db import models


class AuditFieldsMixin(models.Model):
    """Created/updated/deleted by audit columns for business entities."""

    created_by_id = models.UUIDField(null=True, blank=True, db_index=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    deleted_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True
