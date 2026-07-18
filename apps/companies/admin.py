from django.contrib import admin

from apps.companies.models import Company, CompanyLocation, CompanyMember


class CompanyLocationInline(admin.TabularInline):
    model = CompanyLocation
    extra = 0


class CompanyMemberInline(admin.TabularInline):
    model = CompanyMember
    extra = 0
    raw_id_fields = ("recruiter",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "industry",
        "organization_type",
        "company_size",
        "is_active",
        "created_at",
        "is_deleted",
    )
    search_fields = ("name", "legal_name", "slug", "gst_number", "city")
    list_filter = ("is_active", "organization_type", "is_deleted")
    readonly_fields = ("slug", "created_at", "updated_at")
    inlines = [CompanyLocationInline, CompanyMemberInline]
    fieldsets = (
        ("Identity", {"fields": ("name", "legal_name", "slug", "description")}),
        ("Narrative", {"fields": ("mission", "vision", "benefits", "culture")}),
        (
            "Classification",
            {
                "fields": (
                    "industry",
                    "organization_type",
                    "company_size",
                    "founded_year",
                    "gst_number",
                )
            },
        ),
        ("Contact", {"fields": ("website_url", "email", "phone")}),
        ("Branding", {"fields": ("logo_file", "cover_banner_file")}),
        (
            "Address",
            {
                "fields": (
                    "headquarters_location",
                    "address_line",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                )
            },
        ),
        (
            "Social",
            {
                "fields": (
                    "linkedin_url",
                    "twitter_url",
                    "facebook_url",
                    "instagram_url",
                    "youtube_url",
                )
            },
        ),
        (
            "Lifecycle",
            {"fields": ("is_active",)},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CompanyMember)
class CompanyMemberAdmin(admin.ModelAdmin):
    list_display = ("company", "recruiter", "role", "is_primary", "is_active")
    list_filter = ("role", "is_primary", "is_active")
    search_fields = ("company__name",)


@admin.register(CompanyLocation)
class CompanyLocationAdmin(admin.ModelAdmin):
    list_display = ("company", "label", "city", "state", "country", "is_headquarters")
    list_filter = ("is_headquarters", "country")
    search_fields = ("company__name", "city", "label")
