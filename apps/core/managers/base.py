from django.db import models


class BaseQuerySet(models.QuerySet):
    """Shared queryset helpers for domain models."""

    def active(self):
        if hasattr(self.model, "is_deleted"):
            return self.filter(is_deleted=False)
        return self

    def with_status(self, status: str):
        if hasattr(self.model, "status"):
            return self.filter(status=status)
        return self


class BaseManager(models.Manager.from_queryset(BaseQuerySet)):
    """Default manager with shared queryset methods."""

    def get_queryset(self):
        return super().get_queryset()
