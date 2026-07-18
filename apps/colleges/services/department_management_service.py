from apps.audit.services.audit_service import AuditService
from apps.colleges.models import College, CollegeDepartment, Department
from apps.colleges.repositories.college_repository import (
    CollegeDepartmentRepository,
    DepartmentRepository,
)
from apps.colleges.selectors.college_selector import (
    CollegeDepartmentSelector,
    CollegeMemberSelector,
)
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    ConflictException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService


class DepartmentManagementService(BaseService):
    """Manages the academic departments attached to an institution."""

    def __init__(self):
        self.department_repo = DepartmentRepository()
        self.link_repo = CollegeDepartmentRepository()
        self.link_selector = CollegeDepartmentSelector()
        self.member_selector = CollegeMemberSelector()
        self.audit = AuditService()

    @BaseService.atomic
    def add_department(
        self, *, institution: College, college_user, name: str, category: str = ""
    ) -> CollegeDepartment:
        self._ensure_admin(college_user, institution)
        name = (name or "").strip()
        if not name:
            raise ResourceNotFoundException("Department name is required.")

        department = Department.objects.filter(name__iexact=name).first()
        if not department:
            department = self.department_repo.create(
                name=name, category=category or "", created_by_id=college_user.pk
            )

        if (
            self.link_selector.for_college(institution.pk)
            .filter(department=department)
            .exists()
        ):
            raise ConflictException("Department already added to this institution.")

        link = self.link_repo.create(
            college=institution, department=department, created_by_id=college_user.pk
        )
        self._audit(
            institution,
            "institution.department_added",
            college_user.pk,
            {"department_id": str(department.pk), "name": department.name},
        )
        return link

    @BaseService.atomic
    def remove_department(self, *, institution: College, college_user, link_id) -> None:
        self._ensure_admin(college_user, institution)
        link = self.link_selector.for_college(institution.pk).filter(pk=link_id).first()
        if not link:
            raise ResourceNotFoundException("Institution department not found.")
        self.link_repo.soft_delete(link)
        self._audit(
            institution,
            "institution.department_removed",
            college_user.pk,
            {"link_id": str(link_id)},
        )

    def _ensure_admin(self, college_user, institution: College) -> None:
        if not self.member_selector.is_admin(college_user, institution.pk):
            raise PermissionDeniedException(
                "Only institution administrators can manage departments."
            )

    def _audit(
        self, institution: College, event_type: str, actor_id, payload: dict
    ) -> None:
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type=event_type,
            entity_type=EntityReferenceType.FACULTY_COLLEGE,
            entity_id=institution.pk,
            payload=payload,
            actor_type=ActorType.COLLEGE,
            actor_id=actor_id,
        )
