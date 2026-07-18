from django.contrib import admin

from apps.academic_recruitment.models import (
    ProfessorDepartment,
    ProfessorProfile,
    ProfessorQualification,
    Qualification,
)


@admin.register(ProfessorProfile)
class ProfessorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "user",
        "specialization",
        "profile_status",
        "profile_visibility",
        "moderation_status",
        "profile_completeness",
        "is_deleted",
    )
    search_fields = ("first_name", "last_name", "user__email")
    list_filter = (
        "profile_status",
        "profile_visibility",
        "moderation_status",
        "is_deleted",
    )


@admin.register(ProfessorDepartment)
class ProfessorDepartmentAdmin(admin.ModelAdmin):
    list_display = ("professor", "department", "is_deleted")
    list_filter = ("is_deleted",)


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "is_active")
    search_fields = ("name",)


@admin.register(ProfessorQualification)
class ProfessorQualificationAdmin(admin.ModelAdmin):
    list_display = ("professor", "qualification", "year_obtained")
