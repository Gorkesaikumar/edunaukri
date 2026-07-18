from django.contrib import admin

from apps.colleges.models import (
    College,
    CollegeDepartment,
    CollegeMember,
    Department,
    InstitutionCampus,
    InstitutionDocument,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


class CollegeDepartmentInline(admin.TabularInline):
    model = CollegeDepartment
    extra = 0
    raw_id_fields = ("department",)


class CollegeMemberInline(admin.TabularInline):
    model = CollegeMember
    extra = 0
    raw_id_fields = ("college_user",)


class InstitutionCampusInline(admin.TabularInline):
    model = InstitutionCampus
    extra = 0


class InstitutionDocumentInline(admin.TabularInline):
    model = InstitutionDocument
    extra = 0
    raw_id_fields = ("stored_file",)


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "institution_type",
        "ownership_type",
        "city",
        "state",
        "is_active",
        "is_deleted",
    )
    search_fields = ("name", "legal_name", "slug", "city", "aicte_code", "ugc_code")
    list_filter = (
        "is_active",
        "institution_type",
        "ownership_type",
        "profile_status",
        "is_deleted",
    )
    readonly_fields = ("slug", "created_at", "updated_at")
    inlines = [
        CollegeMemberInline,
        CollegeDepartmentInline,
        InstitutionCampusInline,
        InstitutionDocumentInline,
    ]
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "name",
                    "legal_name",
                    "slug",
                    "college_type",
                    "institution_type",
                    "ownership_type",
                    "autonomous_status",
                )
            },
        ),
        (
            "Narrative",
            {
                "fields": (
                    "description",
                    "vision",
                    "mission",
                    "infrastructure_description",
                    "facilities",
                    "placement_cell_details",
                    "research_centers",
                    "hostel_availability",
                    "transportation_facilities",
                )
            },
        ),
        (
            "Academic",
            {
                "fields": (
                    "affiliated_university",
                    "academic_calendar_reference",
                    "programs_offered",
                    "courses_offered",
                )
            },
        ),
        (
            "Accreditation",
            {
                "fields": (
                    "accreditation",
                    "aicte_code",
                    "ugc_code",
                    "naac_grade",
                    "nba_accreditation",
                )
            },
        ),
        (
            "Metrics",
            {
                "fields": (
                    "established_year",
                    "campus_area",
                    "number_of_students",
                    "number_of_faculty",
                )
            },
        ),
        (
            "Contact",
            {
                "fields": (
                    "website_url",
                    "contact_email",
                    "contact_phone",
                    "alternate_phone",
                )
            },
        ),
        ("Branding", {"fields": ("logo_file", "cover_banner_file")}),
        (
            "Address",
            {
                "fields": (
                    "address_line",
                    "city",
                    "district",
                    "state",
                    "country",
                    "pin_code",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Social",
            {
                "fields": (
                    "linkedin_url",
                    "facebook_url",
                    "instagram_url",
                    "twitter_url",
                    "youtube_url",
                )
            },
        ),
        (
            "Lifecycle",
            {"fields": ("is_active", "profile_status", "profile_visibility")},
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
    raw_id_fields = ("logo_file", "cover_banner_file")


@admin.register(CollegeDepartment)
class CollegeDepartmentAdmin(admin.ModelAdmin):
    list_display = ("college", "department", "is_deleted")
    list_filter = ("is_deleted",)
    raw_id_fields = ("college", "department")


@admin.register(CollegeMember)
class CollegeMemberAdmin(admin.ModelAdmin):
    list_display = ("college", "college_user", "role", "is_primary", "is_active")
    list_filter = ("role", "is_primary", "is_active")
    raw_id_fields = ("college", "college_user")


@admin.register(InstitutionCampus)
class InstitutionCampusAdmin(admin.ModelAdmin):
    list_display = ("college", "label", "city", "state", "is_main_campus", "is_deleted")
    list_filter = ("is_main_campus", "is_deleted")
    raw_id_fields = ("college",)


@admin.register(InstitutionDocument)
class InstitutionDocumentAdmin(admin.ModelAdmin):
    list_display = ("college", "document_type", "title", "is_deleted")
    list_filter = ("document_type", "is_deleted")
    raw_id_fields = ("college", "stored_file")
