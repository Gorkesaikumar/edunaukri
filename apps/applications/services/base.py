"""Shared base for Job Application services."""

from apps.audit.services.audit_service import AuditService
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.services.base import BaseService


class ApplicationServiceBase(BaseService):
    def __init__(self):
        self.audit = AuditService()

    def _audit(self, application, event_type: str, actor_id, payload: dict) -> None:
        self.audit.record(
            domain=DomainType.IT,
            event_type=event_type,
            entity_type=EntityReferenceType.IT_JOB_APPLICATION,
            entity_id=application.pk,
            payload=payload,
            actor_type=ActorType.IT_USER,
            actor_id=actor_id,
        )
