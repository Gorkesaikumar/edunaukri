"""Shared base for Faculty Vacancy Management services."""

from apps.audit.services.audit_service import AuditService
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.faculty.models import FacultyVacancy


class FacultyServiceBase(BaseService):
    """Common ownership guard + audit helper for faculty vacancy services."""

    def __init__(self):
        self.member_selector = CollegeMemberSelector()
        self.audit = AuditService()

    def _ensure_manages_vacancy(self, vacancy: FacultyVacancy, college_user) -> None:
        if not self.member_selector.is_member(college_user, vacancy.college_id):
            raise PermissionDeniedException("You do not manage this vacancy.")

    def _audit(
        self, vacancy: FacultyVacancy, event_type: str, actor_id, payload: dict
    ) -> None:
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type=event_type,
            entity_type=EntityReferenceType.FACULTY_VACANCY,
            entity_id=vacancy.pk,
            payload=payload,
            actor_type=ActorType.COLLEGE,
            actor_id=actor_id,
        )
