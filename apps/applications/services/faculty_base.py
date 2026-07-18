"""Shared base for Faculty Application services."""

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.audit.services.audit_service import AuditService
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.services.base import BaseService


class FacultyApplicationServiceBase(BaseService):
    def __init__(self):
        self.audit = AuditService()

    def _audit(
        self, application, event_type: str, actor_id, payload: dict, *, actor=None
    ) -> None:
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type=event_type,
            entity_type=EntityReferenceType.FACULTY_APPLICATION,
            entity_id=application.pk,
            payload=payload,
            actor_type=self._resolve_actor_type(actor),
            actor_id=actor_id,
        )

    @staticmethod
    def _resolve_actor_type(actor) -> str:
        if isinstance(actor, AdminUser):
            return ActorType.ADMIN
        if isinstance(actor, CollegeUser):
            return ActorType.COLLEGE
        if isinstance(actor, ProfessorUser):
            return ActorType.PROFESSOR
        return ActorType.SYSTEM
