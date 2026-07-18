from django.contrib import admin

from apps.jobs.models import (
    JobLocation,
    JobPosting,
    JobPostingSkill,
    JobSeekerSkill,
    SavedJob,
    Skill,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


class JobPostingSkillInline(admin.TabularInline):
    model = JobPostingSkill
    extra = 0
    raw_id_fields = ("skill",)


class JobLocationInline(admin.TabularInline):
    model = JobLocation
    extra = 0


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "job_code",
        "employment_type",
        "work_mode",
        "status",
        "is_featured",
        "is_urgent",
        "published_at",
        "application_count",
        "is_deleted",
    )
    list_filter = (
        "status",
        "employment_type",
        "work_mode",
        "visibility",
        "is_featured",
        "is_urgent",
        "is_template",
        "is_deleted",
    )
    search_fields = ("title", "job_code", "company_name_snapshot", "city")
    readonly_fields = (
        "slug",
        "company_name_snapshot",
        "application_count",
        "view_count",
        "published_at",
        "closed_at",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("company", "posted_by")
    inlines = [JobPostingSkillInline, JobLocationInline]
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "company",
                    "posted_by",
                    "title",
                    "slug",
                    "job_code",
                    "category",
                    "department",
                )
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "description",
                    "requirements",
                    "roles_responsibilities",
                    "benefits",
                    "education_requirement",
                )
            },
        ),
        ("Classification", {"fields": ("employment_type", "work_mode")}),
        (
            "Experience & Salary",
            {
                "fields": (
                    "experience_min",
                    "experience_max",
                    "salary_min",
                    "salary_max",
                    "salary_currency",
                    "salary_visibility",
                )
            },
        ),
        (
            "Capacity",
            {
                "fields": (
                    "vacancies",
                    "joining_timeline",
                    "application_deadline",
                    "hiring_manager",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "country",
                    "state",
                    "city",
                    "office_address",
                    "location",
                    "is_remote",
                )
            },
        ),
        (
            "Visibility",
            {"fields": ("visibility", "is_featured", "is_urgent", "is_template")},
        ),
        (
            "Lifecycle",
            {"fields": ("status", "published_at", "expires_at", "closed_at")},
        ),
        ("Moderation", {"fields": ("moderation_status", "moderation_remarks")}),
        (
            "Counters",
            {"fields": ("application_count", "view_count", "company_name_snapshot")},
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(JobLocation)
class JobLocationAdmin(admin.ModelAdmin):
    list_display = (
        "job_posting",
        "city",
        "state",
        "country",
        "work_mode",
        "is_primary",
        "is_deleted",
    )
    list_filter = ("work_mode", "is_primary", "is_deleted")
    raw_id_fields = ("job_posting",)


@admin.register(JobPostingSkill)
class JobPostingSkillAdmin(admin.ModelAdmin):
    list_display = ("job_posting", "skill", "is_preferred")
    list_filter = ("is_preferred",)
    raw_id_fields = ("job_posting", "skill")


@admin.register(JobSeekerSkill)
class JobSeekerSkillAdmin(admin.ModelAdmin):
    list_display = ("job_seeker", "skill", "proficiency_level")
    raw_id_fields = ("job_seeker", "skill")


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("job_seeker", "job_posting")
    raw_id_fields = ("job_seeker", "job_posting")
