from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import CharField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from apps.accounts.admin_mixins import RoleDisplayAdminMixin
from apps.accounts.admin_role_display import (
    FACULTY_JOB_SEEKER_LABEL,
    FACULTY_RECRUITER_LABEL,
    UNKNOWN_ROLE_LABEL,
    label_for_it_role,
    resolve_it_user_role,
)
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.faculty_user import FacultyUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.it_user_role import ITUserRole
from apps.accounts.models.professor_user import ProfessorUser

_IT_PRIMARY_ROLE = ITUserRole.objects.filter(
    user_id=OuterRef("pk"),
    is_deleted=False,
    is_primary=True,
).values("role")[:1]

_IT_FALLBACK_ROLE = (
    ITUserRole.objects.filter(
        user_id=OuterRef("pk"),
        is_deleted=False,
    )
    .order_by("-is_primary", "granted_at")
    .values("role")[:1]
)


class AdminUserRoleMixin(RoleDisplayAdminMixin):
    role_order_annotation = Value(UNKNOWN_ROLE_LABEL, output_field=CharField())

    def resolve_role_label(self, obj) -> str:
        return UNKNOWN_ROLE_LABEL


@admin.register(AdminUser)
class AdminUserAdmin(AdminUserRoleMixin, BaseUserAdmin):
    list_display = (
        "email",
        "role_display",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_deleted",
        "created_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "is_deleted")
    search_fields = ("email",)
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Status", {"fields": ("is_deleted", "deleted_at")}),
        ("Metadata", {"fields": ("id", "last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


class DomainUserAdmin(RoleDisplayAdminMixin, BaseUserAdmin):
    """Domain portal users — includes secure admin password reset via UserAdmin."""

    list_display = (
        "email",
        "role_display",
        "email_verified",
        "account_status",
        "is_active",
        "is_deleted",
        "created_at",
    )
    list_filter = ("email_verified", "account_status", "is_active", "is_deleted")
    search_fields = ("email",)
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "last_login")
    filter_horizontal = ()

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Account",
            {
                "fields": (
                    "account_status",
                    "email_verified",
                    "is_active",
                    "is_deleted",
                    "deleted_at",
                )
            },
        ),
        ("Security", {"fields": ("failed_login_attempts", "locked_until")}),
        ("Metadata", {"fields": ("id", "last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "account_status",
                    "email_verified",
                    "is_active",
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return self.add_fieldsets
        return fieldsets


@admin.register(ITUser)
class ITUserAdmin(DomainUserAdmin):
    search_fields = ("email", "roles__role")
    role_order_annotation = Coalesce(
        Subquery(_IT_PRIMARY_ROLE),
        Subquery(_IT_FALLBACK_ROLE),
        output_field=CharField(),
    )

    def resolve_role_label(self, obj) -> str:
        role = getattr(obj, "_role_sort_key", None) or resolve_it_user_role(obj)
        return label_for_it_role(role)


@admin.register(ProfessorUser)
class ProfessorUserAdmin(DomainUserAdmin):
    role_order_annotation = Value(FACULTY_JOB_SEEKER_LABEL, output_field=CharField())

    def resolve_role_label(self, obj) -> str:
        return FACULTY_JOB_SEEKER_LABEL


@admin.register(CollegeUser)
class CollegeUserAdmin(DomainUserAdmin):
    role_order_annotation = Value(FACULTY_RECRUITER_LABEL, output_field=CharField())

    def resolve_role_label(self, obj) -> str:
        return FACULTY_RECRUITER_LABEL


@admin.register(FacultyUser)
class FacultyUserAdmin(DomainUserAdmin):
    role_order_annotation = Value(UNKNOWN_ROLE_LABEL, output_field=CharField())

    def resolve_role_label(self, obj) -> str:
        return UNKNOWN_ROLE_LABEL


@admin.register(ITUserRole)
class ITUserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_primary", "granted_at")
    list_filter = ("role", "is_primary")
    search_fields = ("user__email",)
