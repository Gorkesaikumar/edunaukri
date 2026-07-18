from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus, TimelineEventType
from apps.applications.models import JobApplication
from apps.applications.repositories.application_repository import (
    JobApplicationTimelineRepository,
)
from apps.applications.repositories.status_history_repository import (
    JobApplicationStatusHistoryRepository,
)
from apps.core.constants.enums import DomainType
from apps.core.middleware.audit_context import get_audit_actor
from apps.core.services.base import BaseService


class ApplicationHistoryService(BaseService):
    """Maintains status history and rich application timeline events."""

    def __init__(self):
        self.history_repository = JobApplicationStatusHistoryRepository()
        self.timeline_repository = JobApplicationTimelineRepository()

    def record_status_change(
        self,
        application: JobApplication,
        *,
        from_status: str | None,
        to_status: str,
        notes: str = "",
        actor_id=None,
        actor_domain=DomainType.IT,
        metadata: dict | None = None,
        event_type_override: str | None = None,
    ) -> None:
        actor = get_audit_actor()
        changed_by = actor_id or (actor.actor_id if actor else None)
        self.history_repository.create(
            application=application,
            from_status=from_status,
            to_status=to_status,
            changed_by_id=changed_by,
            changed_by_domain=actor_domain,
            notes=notes,
        )
        event_type = event_type_override or (
            TimelineEventType.CREATED
            if from_status is None
            else self._timeline_event_for_status(to_status)
        )
        self.timeline_repository.create(
            application=application,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_id=changed_by,
            actor_domain=actor_domain,
            notes=notes,
            metadata=metadata or {},
            occurred_at=timezone.now(),
        )

    def record_created(self, application: JobApplication, *, actor_id=None) -> None:
        actor = get_audit_actor()
        changed_by = actor_id or (actor.actor_id if actor else None)
        self.timeline_repository.create(
            application=application,
            event_type=TimelineEventType.CREATED,
            from_status=None,
            to_status=application.status,
            actor_id=changed_by,
            actor_domain=DomainType.IT,
            notes="Application submitted.",
            metadata={},
            occurred_at=application.applied_at,
        )

    def record_comment(
        self,
        application: JobApplication,
        *,
        notes: str,
        event_type: str,
        actor_id,
        actor_domain=DomainType.IT,
        metadata: dict | None = None,
    ) -> None:
        self.timeline_repository.create(
            application=application,
            event_type=event_type,
            actor_id=actor_id,
            actor_domain=actor_domain,
            notes=notes,
            metadata=metadata or {},
            occurred_at=timezone.now(),
        )

    @staticmethod
    def _timeline_event_for_status(to_status: str) -> str:
        mapping = {
            JobApplicationStatus.WITHDRAWN: TimelineEventType.WITHDRAW,
            JobApplicationStatus.HIRED: TimelineEventType.HIRE,
            JobApplicationStatus.REJECTED: TimelineEventType.REJECT,
            JobApplicationStatus.OFFER_RELEASED: TimelineEventType.OFFER,
            JobApplicationStatus.OFFER_ACCEPTED: TimelineEventType.OFFER,
        }
        return mapping.get(to_status, TimelineEventType.STATUS_CHANGED)
