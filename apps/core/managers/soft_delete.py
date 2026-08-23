from django.db import models
from django.utils import timezone

from apps.core.managers.base import BaseQuerySet


class SoftDeleteQuerySet(BaseQuerySet):
    def delete(self):
        from django.db import transaction

        with transaction.atomic():
            for obj in self:
                if hasattr(obj, "purge_soft_deleted_dependents"):
                    obj.purge_soft_deleted_dependents()
            return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        from django.db import transaction

        with transaction.atomic():
            for obj in self:
                if hasattr(obj, "purge_soft_deleted_dependents"):
                    obj.purge_soft_deleted_dependents()
            return super().delete()

    def purge(self):
        """Hard-delete all already soft-deleted rows in this queryset."""
        return self.filter(is_deleted=True).hard_delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Return only non-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager exposing all records including soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset()
