from django.utils import timezone

from apps.applications.constants.faculty_enums import (
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)
from apps.applications.models import FacultyApplication
from apps.applications.repositories.application_repository import (
    FacultyApplicationTimelineRepository,
)
from apps.applications.repositories.status_history_repository import (
    FacultyApplicationStatusHistoryRepository,
)
from apps.core.constants.enums import DomainType
from apps.core.middleware.audit_context import get_audit_actor
from apps.core.services.base import BaseService


class FacultyApplicationHistoryService(BaseService):
    """Maintains status history and rich faculty application timeline events."""

    def __init__(self):
        self.history_repository = FacultyApplicationStatusHistoryRepository()
        self.timeline_repository = FacultyApplicationTimelineRepository()

    def record_status_change(
        self,
        application: FacultyApplication,
        *,
        from_status: str | None,
        to_status: str,
        notes: str = "",
        actor_id=None,
        actor_domain=DomainType.FACULTY,
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
        event_type = (
            FacultyTimelineEventType.CREATED
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
            metadata={},
            occurred_at=timezone.now(),
        )

    def record_comment(
        self,
        application: FacultyApplication,
        *,
        notes: str,
        event_type: str,
        actor_id,
        actor_domain=DomainType.FACULTY,
    ) -> None:
        self.timeline_repository.create(
            application=application,
            event_type=event_type,
            actor_id=actor_id,
            actor_domain=actor_domain,
            notes=notes,
            metadata={},
            occurred_at=timezone.now(),
        )

    @staticmethod
    def _timeline_event_for_status(to_status: str) -> str:
        mapping = {
            FacultyApplicationStatus.WITHDRAWN: FacultyTimelineEventType.WITHDRAW,
            FacultyApplicationStatus.JOINED: FacultyTimelineEventType.JOINED,
            FacultyApplicationStatus.REJECTED: FacultyTimelineEventType.REJECT,
            FacultyApplicationStatus.OFFER_RELEASED: FacultyTimelineEventType.OFFER,
            FacultyApplicationStatus.OFFER_ACCEPTED: FacultyTimelineEventType.OFFER,
        }
        return mapping.get(to_status, FacultyTimelineEventType.STATUS_CHANGED)
