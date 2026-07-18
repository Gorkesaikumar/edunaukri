from django.utils import timezone

from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import BusinessLogicException
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy
from apps.faculty.repositories.vacancy_repository import FacultyVacancyRepository
from apps.faculty.services.base import FacultyServiceBase


class FacultyLifecycleService(FacultyServiceBase):
    """Status transitions for vacancies: pause, reopen, close, archive, expire."""

    def __init__(self):
        super().__init__()
        self.vacancy_repo = FacultyVacancyRepository()

    @BaseService.atomic
    def pause(self, *, vacancy: FacultyVacancy, college_user) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status != VacancyStatus.PUBLISHED:
            raise BusinessLogicException("Only published vacancies can be paused.")
        return self._transition(
            vacancy, VacancyStatus.PAUSED, college_user.pk, "vacancy.paused"
        )

    @BaseService.atomic
    def reopen(self, *, vacancy: FacultyVacancy, college_user) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status not in (VacancyStatus.PAUSED, VacancyStatus.CLOSED):
            raise BusinessLogicException(
                "Only paused or closed vacancies can be reopened."
            )
        if not vacancy.college.can_publish_vacancies:
            raise BusinessLogicException("Only verified colleges may reopen vacancies.")
        vacancy = self.vacancy_repo.update(
            vacancy,
            status=VacancyStatus.PUBLISHED,
            closed_at=None,
            published_at=vacancy.published_at or timezone.now(),
            updated_by_id=college_user.pk,
        )
        self._audit(vacancy, "vacancy.reopened", college_user.pk, {})
        return vacancy

    @BaseService.atomic
    def close(self, *, vacancy: FacultyVacancy, college_user) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status not in (
            VacancyStatus.DRAFT,
            VacancyStatus.PUBLISHED,
            VacancyStatus.PAUSED,
            VacancyStatus.PENDING_APPROVAL,
        ):
            raise BusinessLogicException(
                "Vacancy cannot be closed from its current status."
            )
        vacancy = self.vacancy_repo.update(
            vacancy,
            status=VacancyStatus.CLOSED,
            closed_at=timezone.now(),
            updated_by_id=college_user.pk,
        )
        self._audit(vacancy, "vacancy.closed", college_user.pk, {})
        return vacancy

    @BaseService.atomic
    def archive(self, *, vacancy: FacultyVacancy, college_user) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status == VacancyStatus.ARCHIVED:
            return vacancy
        return self._transition(
            vacancy, VacancyStatus.ARCHIVED, college_user.pk, "vacancy.archived"
        )

    @BaseService.atomic
    def expire(self, *, vacancy: FacultyVacancy, actor_id=None) -> FacultyVacancy:
        """Mark a published vacancy as expired (used by scheduled expiry sweeps)."""
        if vacancy.status != VacancyStatus.PUBLISHED:
            raise BusinessLogicException("Only published vacancies can expire.")
        return self._transition(
            vacancy, VacancyStatus.EXPIRED, actor_id, "vacancy.expired"
        )

    @BaseService.atomic
    def admin_close(self, *, vacancy: FacultyVacancy, admin_id) -> FacultyVacancy:
        if vacancy.status not in (
            VacancyStatus.DRAFT,
            VacancyStatus.PUBLISHED,
            VacancyStatus.PAUSED,
            VacancyStatus.PENDING_APPROVAL,
        ):
            raise BusinessLogicException(
                "Vacancy cannot be closed from its current status."
            )
        vacancy = self.vacancy_repo.update(
            vacancy,
            status=VacancyStatus.CLOSED,
            closed_at=timezone.now(),
            updated_by_id=admin_id,
        )
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type="vacancy.closed",
            entity_type=EntityReferenceType.FACULTY_VACANCY,
            entity_id=vacancy.pk,
            payload={"status": VacancyStatus.CLOSED},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return vacancy

    @BaseService.atomic
    def admin_archive(self, *, vacancy: FacultyVacancy, admin_id) -> FacultyVacancy:
        if vacancy.status == VacancyStatus.ARCHIVED:
            return vacancy
        vacancy = self.vacancy_repo.update(
            vacancy, status=VacancyStatus.ARCHIVED, updated_by_id=admin_id
        )
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type="vacancy.archived",
            entity_type=EntityReferenceType.FACULTY_VACANCY,
            entity_id=vacancy.pk,
            payload={"status": VacancyStatus.ARCHIVED},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return vacancy

    def _transition(
        self, vacancy: FacultyVacancy, status: str, actor_id, event_type: str
    ) -> FacultyVacancy:
        vacancy = self.vacancy_repo.update(
            vacancy, status=status, updated_by_id=actor_id
        )
        self._audit(vacancy, event_type, actor_id, {"status": status})
        return vacancy
