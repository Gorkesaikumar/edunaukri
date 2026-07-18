from django.contrib import admin

from apps.admin_panel.models import PlatformSetting


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "category", "is_active", "updated_at")
    list_filter = ("category", "is_active", "is_deleted")
    search_fields = ("key", "description")
