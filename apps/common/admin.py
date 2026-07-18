"""Django Admin registrations for Common. Phase 1 implementation."""

from django.contrib import admin

from apps.common.models import PlatformActivity, Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "author_name",
        "designation",
        "organization_name",
        "domain",
        "rating",
        "is_verified",
        "is_active",
        "published_at",
    )
    list_filter = ("domain", "is_verified", "is_active", "visibility")
    search_fields = ("author_name", "designation", "organization_name", "quote")
    ordering = ("-published_at", "-created_at")


@admin.register(PlatformActivity)
class PlatformActivityAdmin(admin.ModelAdmin):
    list_display = (
        "org_name",
        "activity_type",
        "domain",
        "headline",
        "is_active",
        "created_at",
    )
    list_filter = ("domain", "activity_type", "is_active")
    search_fields = ("org_name", "headline")
    ordering = ("-created_at",)
