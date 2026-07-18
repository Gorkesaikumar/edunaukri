"""Append-only security activity log for account settings."""

from __future__ import annotations

from apps.authentication.models import SecurityAuditEvent
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService


class SecurityAuditService(BaseService):
    def record(
        self,
        *,
        domain: str,
        user_id,
        event_type: str,
        title: str,
        description: str = "",
        ip_address: str | None = None,
        metadata: dict | None = None,
    ) -> SecurityAuditEvent:
        return SecurityAuditEvent.objects.create(
            domain=domain,
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            ip_address=ip_address,
            metadata=metadata or {},
        )

    def list_for_user(
        self, *, domain: str, user_id, limit: int = 25
    ) -> list[SecurityAuditEvent]:
        return list(
            SecurityAuditEvent.objects.filter(
                domain=domain, user_id=user_id, is_deleted=False
            ).order_by("-occurred_at")[:limit]
        )

    def list_activity_for_user(
        self,
        *,
        domain: str,
        user_id,
        limit: int = 25,
        exclude_event_types: frozenset[str] | None = None,
    ) -> list[SecurityAuditEvent]:
        """User-facing security activity — excludes noisy background events."""
        from apps.authentication.constants.auth_events import AUTH_TOKEN_REFRESH

        excluded = exclude_event_types or frozenset({AUTH_TOKEN_REFRESH})
        qs = SecurityAuditEvent.objects.filter(
            domain=domain, user_id=user_id, is_deleted=False
        )
        if excluded:
            qs = qs.exclude(event_type__in=excluded)
        return list(qs.order_by("-occurred_at")[:limit])

    @staticmethod
    def serialize_event(event: SecurityAuditEvent) -> dict:
        from django.utils import timezone

        occurred = timezone.localtime(event.occurred_at)
        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "ip_address": event.ip_address or "",
            "occurred_at": event.occurred_at.isoformat(),
            "occurred_label": occurred.strftime("%b %d, %Y · %I:%M %p"),
        }
