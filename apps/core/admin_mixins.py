from django.contrib import messages
from django.db import models, transaction
from django.db.models.deletion import ProtectedError
from django.utils.translation import ngettext


class SoftDeleteAdminMixin:
    """ModelAdmin mixin that safely handles soft-deletable entities and pre-purges soft-deleted dependents."""

    def get_deleted_objects(self, objs, request):
        with transaction.atomic():
            for obj in objs:
                if hasattr(obj, "purge_soft_deleted_dependents"):
                    obj.purge_soft_deleted_dependents()
            try:
                return super().get_deleted_objects(objs, request)
            except ProtectedError as e:
                # Format a clear, meaningful message showing only active protected objects
                active_protected = [
                    o for o in e.protected_objects if getattr(o, "is_deleted", False) is False
                ]
                if active_protected:
                    raise ProtectedError(
                        f"Cannot delete because active dependent records exist: {active_protected}",
                        active_protected,
                    ) from e
                raise e

    def delete_model(self, request, obj):
        with transaction.atomic():
            if hasattr(obj, "purge_soft_deleted_dependents"):
                obj.purge_soft_deleted_dependents()
            obj.delete()

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for obj in queryset:
                if hasattr(obj, "purge_soft_deleted_dependents"):
                    obj.purge_soft_deleted_dependents()
            queryset.delete()
