from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import VacancyStatus, VacancyVisibility
from apps.faculty.models import FacultyVacancy
from apps.faculty.repositories.vacancy_repository import FacultyVacancyRepository
from apps.faculty.services.base import FacultyServiceBase


class FacultyVisibilityService(FacultyServiceBase):
    """Featured / urgent flags, visibility scope, and public-visibility rules."""

    def __init__(self):
        super().__init__()
        self.vacancy_repo = FacultyVacancyRepository()

    @BaseService.atomic
    def set_featured(
        self, *, vacancy: FacultyVacancy, college_user, value: bool
    ) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        vacancy = self.vacancy_repo.update(
            vacancy, is_featured=bool(value), updated_by_id=college_user.pk
        )
        self._audit(
            vacancy,
            "vacancy.featured_changed",
            college_user.pk,
            {"is_featured": bool(value)},
        )
        return vacancy

    @BaseService.atomic
    def set_urgent(
        self, *, vacancy: FacultyVacancy, college_user, value: bool
    ) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        vacancy = self.vacancy_repo.update(
            vacancy, is_urgent=bool(value), updated_by_id=college_user.pk
        )
        self._audit(
            vacancy,
            "vacancy.urgent_changed",
            college_user.pk,
            {"is_urgent": bool(value)},
        )
        return vacancy

    @BaseService.atomic
    def set_visibility(
        self, *, vacancy: FacultyVacancy, college_user, visibility: str
    ) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if visibility not in VacancyVisibility.values:
            raise ValidationException("Invalid visibility value.")
        vacancy = self.vacancy_repo.update(
            vacancy, visibility=visibility, updated_by_id=college_user.pk
        )
        self._audit(
            vacancy,
            "vacancy.visibility_changed",
            college_user.pk,
            {"visibility": visibility},
        )
        return vacancy

    @BaseService.atomic
    def admin_set_featured(
        self, *, vacancy: FacultyVacancy, admin_id, value: bool
    ) -> FacultyVacancy:
        vacancy = self.vacancy_repo.update(
            vacancy, is_featured=bool(value), updated_by_id=admin_id
        )
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type="vacancy.featured_changed",
            entity_type=EntityReferenceType.FACULTY_VACANCY,
            entity_id=vacancy.pk,
            payload={"is_featured": bool(value)},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return vacancy

    @staticmethod
    def is_publicly_visible(vacancy: FacultyVacancy) -> bool:
        return (
            vacancy.status == VacancyStatus.PUBLISHED
            and vacancy.visibility == VacancyVisibility.PUBLIC
            and not vacancy.is_deleted
        )
