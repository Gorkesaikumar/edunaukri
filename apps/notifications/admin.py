from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient_domain",
        "recipient_id",
        "event_type",
        "is_read",
        "created_at",
    )
    list_filter = ("recipient_domain", "event_type", "is_read", "is_deleted")
    search_fields = ("title", "body")
