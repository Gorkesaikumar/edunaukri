from django.utils import timezone

from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import BusinessLogicException
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import PUBLISHABLE_STATUSES, VacancyStatus
from apps.faculty.models import FacultyVacancy
from apps.faculty.repositories.vacancy_repository import FacultyVacancyRepository
from apps.faculty.services.base import FacultyServiceBase
from apps.faculty.services.vacancy_validation_service import FacultyValidationService


class FacultyPublicationService(FacultyServiceBase):
    """Publish / unpublish vacancies and enforce the verified-college rule."""

    def __init__(self):
        super().__init__()
        self.vacancy_repo = FacultyVacancyRepository()
        self.validation = FacultyValidationService()

    @BaseService.atomic
    def publish(self, *, vacancy: FacultyVacancy, college_user) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status not in PUBLISHABLE_STATUSES:
            raise BusinessLogicException(
                "Only draft, pending or paused vacancies can be published."
            )
        if not vacancy.college.can_publish_vacancies:
            raise BusinessLogicException(
                "Only verified colleges may publish faculty vacancies."
            )
        self.validation.validate_can_publish(vacancy)

        vacancy = self.vacancy_repo.update(
            vacancy,
            status=VacancyStatus.PUBLISHED,
            published_at=vacancy.published_at or timezone.now(),
            updated_by_id=college_user.pk,
        )
        self._audit(vacancy, "vacancy.published", college_user.pk, {})
        return vacancy

    @BaseService.atomic
    def unpublish(self, *, vacancy: FacultyVacancy, college_user) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status != VacancyStatus.PUBLISHED:
            raise BusinessLogicException("Only published vacancies can be unpublished.")
        vacancy = self.vacancy_repo.update(
            vacancy, status=VacancyStatus.DRAFT, updated_by_id=college_user.pk
        )
        self._audit(vacancy, "vacancy.unpublished", college_user.pk, {})
        return vacancy

    @BaseService.atomic
    def admin_approve(
        self, *, vacancy: FacultyVacancy, admin_id, remarks: str = ""
    ) -> FacultyVacancy:
        """Admin approval: bypasses college-verified checks."""
        vacancy = self.vacancy_repo.update(
            vacancy,
            status=VacancyStatus.PUBLISHED,
            published_at=vacancy.published_at or timezone.now(),
            updated_by_id=admin_id,
        )
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type="vacancy.approved",
            entity_type=EntityReferenceType.FACULTY_VACANCY,
            entity_id=vacancy.pk,
            payload={"status": VacancyStatus.PUBLISHED, "remarks": remarks},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return vacancy

    @BaseService.atomic
    def admin_reject(
        self, *, vacancy: FacultyVacancy, admin_id, remarks: str = ""
    ) -> FacultyVacancy:
        """Admin rejection: moves vacancy to REJECTED status."""
        vacancy = self.vacancy_repo.update(
            vacancy,
            status=VacancyStatus.REJECTED,
            updated_by_id=admin_id,
        )
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type="vacancy.rejected",
            entity_type=EntityReferenceType.FACULTY_VACANCY,
            entity_id=vacancy.pk,
            payload={"status": VacancyStatus.REJECTED, "remarks": remarks},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return vacancy
