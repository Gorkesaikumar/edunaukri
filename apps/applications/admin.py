from django.contrib import admin

from apps.applications.models import (
    FacultyApplication,
    FacultyApplicationStatusHistory,
    FacultyApplicationTimelineEvent,
    JobApplication,
    JobApplicationStatusHistory,
    JobApplicationTimelineEvent,
)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "job_title_snapshot",
        "applicant_name_snapshot",
        "company_name_snapshot",
        "status",
        "source",
        "applied_at",
        "is_deleted",
    )
    list_filter = ("status", "source", "is_deleted")
    search_fields = (
        "applicant_name_snapshot",
        "job_title_snapshot",
        "company_name_snapshot",
    )
    raw_id_fields = ("job_posting", "job_seeker", "company", "resume_file")
    readonly_fields = (
        "resume_snapshot",
        "applied_at",
        "status_changed_at",
        "hired_at",
        "placed_at",
    )


@admin.register(JobApplicationStatusHistory)
class JobApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "from_status", "to_status", "changed_at")
    list_filter = ("to_status",)


@admin.register(JobApplicationTimelineEvent)
class JobApplicationTimelineEventAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "event_type",
        "from_status",
        "to_status",
        "occurred_at",
    )
    list_filter = ("event_type",)


@admin.register(FacultyApplication)
class FacultyApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "vacancy_title_snapshot",
        "applicant_name_snapshot",
        "college_name_snapshot",
        "department",
        "status",
        "source",
        "applied_at",
        "is_deleted",
    )
    list_filter = ("status", "source", "is_deleted")
    search_fields = (
        "applicant_name_snapshot",
        "vacancy_title_snapshot",
        "college_name_snapshot",
        "department",
    )
    raw_id_fields = ("vacancy", "professor", "college", "cv_file")
    readonly_fields = (
        "cv_snapshot",
        "qualification_snapshot",
        "specialization_snapshot",
        "experience_snapshot",
        "certificates_snapshot",
        "applied_at",
        "status_changed_at",
        "joined_at",
        "placed_at",
    )


@admin.register(FacultyApplicationStatusHistory)
class FacultyApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "from_status", "to_status", "changed_at")
    list_filter = ("to_status",)


@admin.register(FacultyApplicationTimelineEvent)
class FacultyApplicationTimelineEventAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "event_type",
        "from_status",
        "to_status",
        "occurred_at",
    )
    list_filter = ("event_type",)
