"""Reusable Django Admin mixins for accounts."""

from __future__ import annotations

from django.contrib import admin

from apps.accounts.admin_role_display import UNKNOWN_ROLE_LABEL


class RoleDisplayAdminMixin:
    """Read-only Role column and detail field for user admin classes."""

    role_order_annotation = None

    def resolve_role_label(self, obj) -> str:
        return UNKNOWN_ROLE_LABEL

    @admin.display(description="Role", ordering="_role_sort_key")
    def role_display(self, obj):
        return self.resolve_role_label(obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.role_order_annotation is not None:
            return qs.annotate(_role_sort_key=self.role_order_annotation)
        return qs

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and "role_display" not in readonly:
            readonly.append("role_display")
        return readonly

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return fieldsets

        updated = []
        for title, options in fieldsets:
            fields = list(options.get("fields", ()))
            if (
                title in {"Account", "Permissions", "Status"}
                and "role_display" not in fields
            ):
                fields.insert(0, "role_display")
                options = {**options, "fields": tuple(fields)}
            updated.append((title, options))
        return updated
