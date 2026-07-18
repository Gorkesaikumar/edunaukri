from django.utils.dateparse import parse_datetime

from apps.audit.models import AuditEvent
from apps.core.selectors.read import ReadSelector


class AuditSelector(ReadSelector):
    model = AuditEvent

    def search(
        self,
        *,
        domain: str | None = None,
        event_type: str | None = None,
        entity_type: str | None = None,
        entity_id=None,
        actor_id=None,
        occurred_after=None,
        occurred_before=None,
        q: str | None = None,
    ):
        queryset = self.get_queryset().order_by("-occurred_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)
        if occurred_after:
            dt = (
                parse_datetime(occurred_after)
                if isinstance(occurred_after, str)
                else occurred_after
            )
            if dt:
                queryset = queryset.filter(occurred_at__gte=dt)
        if occurred_before:
            dt = (
                parse_datetime(occurred_before)
                if isinstance(occurred_before, str)
                else occurred_before
            )
            if dt:
                queryset = queryset.filter(occurred_at__lte=dt)
        if q:
            queryset = queryset.filter(event_type__icontains=q)
        return queryset
