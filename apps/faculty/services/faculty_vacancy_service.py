import uuid

from apps.colleges.selectors.college_selector import CollegeSelector
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService
from apps.core.utils.strings import slugify
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy
from apps.faculty.repositories.vacancy_repository import (
    FacultyVacancyCampusRepository,
    FacultyVacancyRepository,
)
from apps.faculty.services.base import FacultyServiceBase
from apps.faculty.services.vacancy_validation_service import FacultyValidationService

WRITABLE_FIELDS = (
    "title",
    "vacancy_code",
    "department",
    "designation",
    "description",
    "requirements",
    "roles_responsibilities",
    "teaching_responsibilities",
    "research_expectations",
    "administrative_responsibilities",
    "benefits",
    "facilities",
    "accommodation",
    "employment_type",
    "work_type",
    "recruitment_category",
    "contract_duration",
    "minimum_qualification",
    "preferred_qualification",
    "qualification_required",
    "specialization_required",
    "experience_min",
    "experience_max",
    "research_experience",
    "industry_experience",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_visibility",
    "vacancy_count",
    "joining_date",
    "application_deadline",
    "hiring_committee",
    "country",
    "state",
    "district",
    "city",
    "campus",
    "visibility",
    "is_template",
    "expires_at",
)

EDITABLE_STATUSES = (
    VacancyStatus.DRAFT,
    VacancyStatus.PENDING_APPROVAL,
    VacancyStatus.PUBLISHED,
    VacancyStatus.PAUSED,
)

DELETABLE_STATUSES = (
    VacancyStatus.DRAFT,
    VacancyStatus.CLOSED,
    VacancyStatus.PAUSED,
    VacancyStatus.ARCHIVED,
)

_CLONED_FIELDS = tuple(
    f for f in WRITABLE_FIELDS if f not in ("title", "vacancy_code", "expires_at")
)


class FacultyVacancyService(FacultyServiceBase):
    """Create, update, duplicate and delete faculty vacancies."""

    def __init__(self):
        super().__init__()
        self.vacancy_repo = FacultyVacancyRepository()
        self.campus_repo = FacultyVacancyCampusRepository()
        self.college_selector = CollegeSelector()
        self.validation = FacultyValidationService()

    @BaseService.atomic
    def create_vacancy(self, *, college_user, data: dict) -> FacultyVacancy:
        self.validation.validate_payload(data, partial=False)

        college = self.college_selector.get_or_none(data.get("college_id"))
        if not college:
            raise ResourceNotFoundException("College not found.")
        self._ensure_college_membership(college, college_user)
        self._guard_duplicate(college, data["title"])

        payload = {key: data[key] for key in WRITABLE_FIELDS if key in data}
        vacancy = self.vacancy_repo.create(
            college=college,
            posted_by=college_user,
            slug=self._unique_slug(college, data["title"]),
            college_name_snapshot=college.name,
            status=VacancyStatus.DRAFT,
            created_by_id=college_user.pk,
            **payload,
        )
        self._sync_campuses(vacancy, data.get("campuses"), college_user.pk)
        self._audit(
            vacancy, "vacancy.created", college_user.pk, {"title": vacancy.title}
        )
        return vacancy

    @BaseService.atomic
    def update_vacancy(
        self, *, vacancy: FacultyVacancy, college_user, data: dict
    ) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status not in EDITABLE_STATUSES:
            raise BusinessLogicException("This vacancy can no longer be edited.")

        self.validation.validate_payload(data, partial=True)
        payload = {key: data[key] for key in WRITABLE_FIELDS if key in data}
        if payload:
            vacancy = self.vacancy_repo.update(
                vacancy, updated_by_id=college_user.pk, **payload
            )
        if "campuses" in data:
            self._sync_campuses(
                vacancy, data.get("campuses"), college_user.pk, replace=True
            )

        self._audit(
            vacancy, "vacancy.updated", college_user.pk, {"fields": sorted(payload)}
        )
        return vacancy

    @BaseService.atomic
    def duplicate_vacancy(
        self, *, vacancy: FacultyVacancy, college_user
    ) -> FacultyVacancy:
        self._ensure_manages_vacancy(vacancy, college_user)
        payload = {field: getattr(vacancy, field) for field in _CLONED_FIELDS}
        clone = self.vacancy_repo.create(
            college=vacancy.college,
            posted_by=college_user,
            title=f"{vacancy.title} (Copy)",
            slug=self._unique_slug(vacancy.college, vacancy.title),
            college_name_snapshot=vacancy.college.name,
            status=VacancyStatus.DRAFT,
            created_by_id=college_user.pk,
            **payload,
        )
        for campus in vacancy.campuses.filter(is_deleted=False):
            self.campus_repo.create(
                vacancy=clone,
                country=campus.country,
                state=campus.state,
                district=campus.district,
                city=campus.city,
                campus=campus.campus,
                work_type=campus.work_type,
                is_primary=campus.is_primary,
                created_by_id=college_user.pk,
            )
        self._audit(
            clone, "vacancy.duplicated", college_user.pk, {"source_id": str(vacancy.pk)}
        )
        return clone

    @BaseService.atomic
    def soft_delete(self, *, vacancy: FacultyVacancy, college_user) -> None:
        self._ensure_manages_vacancy(vacancy, college_user)
        if vacancy.status not in DELETABLE_STATUSES:
            raise BusinessLogicException(
                "Only draft, paused, closed, or archived vacancies can be deleted."
            )
        vacancy.deleted_by_id = college_user.pk
        vacancy.save(update_fields=["deleted_by_id"])
        self.vacancy_repo.soft_delete(vacancy)
        self._audit(vacancy, "vacancy.deleted", college_user.pk, {})

    def _ensure_college_membership(self, college, college_user) -> None:
        if not self.member_selector.is_member(college_user, college.pk):
            raise PermissionDeniedException("You are not a member of this institution.")

    def _guard_duplicate(self, college, title: str) -> None:
        active_statuses = (
            VacancyStatus.DRAFT,
            VacancyStatus.PENDING_APPROVAL,
            VacancyStatus.PUBLISHED,
            VacancyStatus.PAUSED,
        )
        if FacultyVacancy.objects.filter(
            college=college, title__iexact=title.strip(), status__in=active_statuses
        ).exists():
            raise ConflictException(
                "An active vacancy with this title already exists for this institution."
            )

    def _unique_slug(self, college, title: str) -> str:
        base = slugify(title)[:340] or "vacancy"
        slug = base
        while FacultyVacancy.all_objects.filter(college=college, slug=slug).exists():
            suffix = f"-{uuid.uuid4().hex[:6]}"
            slug = f"{base[: 350 - len(suffix)]}{suffix}"
        return slug

    def _sync_campuses(
        self, vacancy: FacultyVacancy, campuses, actor_id, *, replace: bool = False
    ) -> None:
        if campuses is None:
            return
        if replace:
            self.campus_repo.filter_by(vacancy=vacancy).update(is_deleted=True)
        for item in campuses:
            self.campus_repo.create(
                vacancy=vacancy,
                country=item.get("country", ""),
                state=item.get("state", ""),
                district=item.get("district", ""),
                city=item.get("city", ""),
                campus=item.get("campus", ""),
                work_type=item.get("work_type", "onsite"),
                is_primary=bool(item.get("is_primary", False)),
                created_by_id=actor_id,
            )
