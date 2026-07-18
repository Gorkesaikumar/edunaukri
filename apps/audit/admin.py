from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "domain", "actor_type", "entity_type", "occurred_at")
    list_filter = ("domain", "event_type", "actor_type")
    search_fields = ("event_type", "entity_type", "request_id", "payload_hash")
    readonly_fields = (
        "id",
        "domain",
        "event_type",
        "entity_type",
        "entity_id",
        "actor_type",
        "actor_id",
        "ip_address",
        "user_agent",
        "request_id",
        "payload_hash",
        "payload",
        "occurred_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
