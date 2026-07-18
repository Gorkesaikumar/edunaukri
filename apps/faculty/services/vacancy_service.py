from django.utils import timezone

from apps.core.exceptions.domain_exceptions import BusinessLogicException
from apps.core.services.base import BaseService
from apps.core.utils.strings import slugify
from apps.faculty.models import FacultyVacancy
from apps.faculty.repositories.vacancy_repository import FacultyVacancyRepository
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector


class VacancyPostingService(BaseService):
    """Legacy vacancy service backing the /api/v1/faculty/vacancies/* endpoints.

    Retained for backward compatibility. New functionality lives in the
    enterprise Faculty Vacancy Management services (FacultyVacancyService, etc.).
    """

    def __init__(self):
        self.vacancy_repo = FacultyVacancyRepository()
        self.vacancy_selector = FacultyVacancySelector()

    @BaseService.atomic
    def create_draft(self, *, college, college_user, data: dict) -> FacultyVacancy:
        slug = data.get("slug") or slugify(data["title"])[:350]
        return self.vacancy_repo.create(
            college=college,
            posted_by=college_user,
            title=data["title"],
            slug=slug,
            description=data["description"],
            requirements=data.get("requirements", ""),
            employment_type=data.get(
                "employment_type", FacultyVacancy.EmploymentType.FULL_TIME
            ),
            experience_min=data.get("experience_min"),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            department=data.get("department", ""),
            college_name_snapshot=college.name,
            created_by_id=college_user.pk,
        )

    @BaseService.atomic
    def publish(self, vacancy: FacultyVacancy, *, college_user) -> FacultyVacancy:
        self._ensure_college_owns_vacancy(vacancy, college_user)
        if vacancy.status != FacultyVacancy.VacancyStatus.DRAFT:
            raise BusinessLogicException("Only draft vacancies can be published.")
        if not vacancy.college.can_publish_vacancies:
            raise BusinessLogicException(
                "Only verified colleges may publish faculty vacancies."
            )
        return self.vacancy_repo.update(
            vacancy,
            status=FacultyVacancy.VacancyStatus.PUBLISHED,
            published_at=timezone.now(),
            updated_by_id=college_user.pk,
        )

    @BaseService.atomic
    def update_draft(
        self, vacancy: FacultyVacancy, *, college_user, data: dict
    ) -> FacultyVacancy:
        self._ensure_college_owns_vacancy(vacancy, college_user)
        if vacancy.status != FacultyVacancy.VacancyStatus.DRAFT:
            raise BusinessLogicException("Only draft vacancies can be edited.")
        writable = {
            "title",
            "description",
            "requirements",
            "employment_type",
            "experience_min",
            "salary_min",
            "salary_max",
        }
        payload = {key: data[key] for key in writable if key in data}
        if not payload:
            return vacancy
        return self.vacancy_repo.update(
            vacancy, updated_by_id=college_user.pk, **payload
        )

    @BaseService.atomic
    def close(self, vacancy: FacultyVacancy, *, college_user) -> FacultyVacancy:
        self._ensure_college_owns_vacancy(vacancy, college_user)
        if vacancy.status not in (
            FacultyVacancy.VacancyStatus.DRAFT,
            FacultyVacancy.VacancyStatus.PUBLISHED,
        ):
            raise BusinessLogicException(
                "Vacancy cannot be closed from its current status."
            )
        return self.vacancy_repo.update(
            vacancy,
            status=FacultyVacancy.VacancyStatus.CLOSED,
            updated_by_id=college_user.pk,
        )

    def _ensure_college_owns_vacancy(
        self, vacancy: FacultyVacancy, college_user
    ) -> None:
        from apps.colleges.selectors.college_selector import CollegeMemberSelector

        if (
            not CollegeMemberSelector()
            .for_user(college_user)
            .filter(college_id=vacancy.college_id)
            .exists()
        ):
            raise BusinessLogicException("You do not manage this vacancy.")
