from django.contrib import admin

from apps.faculty.models import (
    FacultyVacancy,
    FacultyVacancyCampus,
    FacultyVacancyDepartment,
    SavedVacancy,
)


class FacultyVacancyCampusInline(admin.TabularInline):
    model = FacultyVacancyCampus
    extra = 0


class FacultyVacancyDepartmentInline(admin.TabularInline):
    model = FacultyVacancyDepartment
    extra = 0
    raw_id_fields = ("department",)


@admin.register(FacultyVacancy)
class FacultyVacancyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "college",
        "vacancy_code",
        "designation",
        "employment_type",
        "work_type",
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
        "work_type",
        "designation",
        "recruitment_category",
        "visibility",
        "is_featured",
        "is_urgent",
        "is_template",
        "is_deleted",
    )
    search_fields = (
        "title",
        "vacancy_code",
        "college_name_snapshot",
        "department",
        "city",
    )
    readonly_fields = (
        "slug",
        "college_name_snapshot",
        "application_count",
        "view_count",
        "published_at",
        "closed_at",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("college", "posted_by")
    inlines = [FacultyVacancyCampusInline, FacultyVacancyDepartmentInline]
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "college",
                    "posted_by",
                    "title",
                    "slug",
                    "vacancy_code",
                    "department",
                    "designation",
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
                    "teaching_responsibilities",
                    "research_expectations",
                    "administrative_responsibilities",
                    "benefits",
                    "facilities",
                    "accommodation",
                )
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    "employment_type",
                    "work_type",
                    "recruitment_category",
                    "contract_duration",
                )
            },
        ),
        (
            "Qualifications",
            {
                "fields": (
                    "minimum_qualification",
                    "preferred_qualification",
                    "qualification_required",
                    "specialization_required",
                )
            },
        ),
        (
            "Experience",
            {
                "fields": (
                    "experience_min",
                    "experience_max",
                    "research_experience",
                    "industry_experience",
                )
            },
        ),
        (
            "Compensation",
            {
                "fields": (
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
                    "vacancy_count",
                    "joining_date",
                    "application_deadline",
                    "hiring_committee",
                )
            },
        ),
        ("Location", {"fields": ("country", "state", "district", "city", "campus")}),
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
            {"fields": ("application_count", "view_count", "college_name_snapshot")},
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(FacultyVacancyCampus)
class FacultyVacancyCampusAdmin(admin.ModelAdmin):
    list_display = (
        "vacancy",
        "campus",
        "city",
        "district",
        "state",
        "country",
        "work_type",
        "is_primary",
        "is_deleted",
    )
    list_filter = ("work_type", "is_primary", "is_deleted")
    raw_id_fields = ("vacancy",)


@admin.register(FacultyVacancyDepartment)
class FacultyVacancyDepartmentAdmin(admin.ModelAdmin):
    list_display = ("vacancy", "department")
    raw_id_fields = ("vacancy", "department")


@admin.register(SavedVacancy)
class SavedVacancyAdmin(admin.ModelAdmin):
    list_display = ("professor", "vacancy")
    raw_id_fields = ("professor", "vacancy")
