from django.contrib import admin

from apps.it_recruitment.models import (
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProfile,
    RecruiterProfile,
)


@admin.register(JobSeekerExperience)
class JobSeekerExperienceAdmin(admin.ModelAdmin):
    list_display = ("job_seeker", "company_name", "title", "is_current", "is_deleted")
    search_fields = (
        "company_name",
        "title",
        "job_seeker__first_name",
        "job_seeker__last_name",
    )
    list_filter = ("is_current", "is_deleted")


@admin.register(JobSeekerEducation)
class JobSeekerEducationAdmin(admin.ModelAdmin):
    list_display = ("job_seeker", "institution", "degree", "end_year", "is_deleted")
    search_fields = ("institution", "degree")
    list_filter = ("is_deleted",)


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "user",
        "profile_status",
        "profile_visibility",
        "profile_completeness",
        "created_at",
        "is_deleted",
    )
    search_fields = ("first_name", "last_name", "user__email")
    list_filter = ("profile_status", "profile_visibility", "is_deleted")


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "user",
        "designation",
        "profile_status",
        "profile_visibility",
        "created_at",
        "is_deleted",
    )
    search_fields = ("first_name", "last_name", "user__email", "official_email")
    list_filter = ("profile_status", "is_deleted")
