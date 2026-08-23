import uuid

from django.db import models
from django.utils import timezone

from apps.core.managers import ActiveManager, SoftDeleteManager


class UUIDPrimaryKeyMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = SoftDeleteManager()

    class Meta:
        abstract = True
        default_manager_name = "objects"
        base_manager_name = "objects"

    def purge_soft_deleted_dependents(self):
        """Purge (hard-delete) any soft-deleted child objects linked to this instance."""
        from django.db import transaction

        with transaction.atomic():
            for field in self._meta.get_fields():
                if (field.one_to_many or field.one_to_one) and field.auto_created and not field.concrete:
                    related_model = field.related_model
                    if not related_model:
                        continue
                    remote_name = field.remote_field.name if field.remote_field else None
                    if not remote_name:
                        continue
                    if hasattr(related_model, "all_objects") and hasattr(related_model, "is_deleted"):
                        try:
                            soft_deleted_qs = related_model.all_objects.filter(
                                **{remote_name: self, "is_deleted": True}
                            )
                            if soft_deleted_qs.exists():
                                if hasattr(soft_deleted_qs, "hard_delete"):
                                    soft_deleted_qs.hard_delete()
                                else:
                                    soft_deleted_qs.delete()
                        except Exception:
                            pass

    def delete(self, using=None, keep_parents=False):
        from django.db import transaction

        with transaction.atomic():
            self.purge_soft_deleted_dependents()
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        from django.db import transaction

        with transaction.atomic():
            self.purge_soft_deleted_dependents()
            return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
