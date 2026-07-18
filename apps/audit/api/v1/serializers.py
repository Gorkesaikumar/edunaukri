from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "domain",
            "event_type",
            "entity_type",
            "entity_id",
            "actor_type",
            "actor_id",
            "ip_address",
            "request_id",
            "payload",
            "occurred_at",
        )
        read_only_fields = fields
