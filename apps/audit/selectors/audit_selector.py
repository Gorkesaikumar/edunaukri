from apps.audit.models import AuditEvent
from apps.core.selectors.read import ReadSelector


class AuditEventSelector(ReadSelector):
    model = AuditEvent

    def filter_events(self, *, domain=None, event_type=None, entity_id=None):
        queryset = self.get_queryset().order_by("-occurred_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset
