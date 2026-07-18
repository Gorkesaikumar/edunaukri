from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from apps.core.selectors.read import ReadSelector
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy

_SORT_MAP = {
    "recent": "-published_at",
    "oldest": "published_at",
    "salary_high": "-salary_max",
    "salary_low": "salary_min",
    "title": "title",
}


def _to_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


class VacancySearchSelector(ReadSelector):
    """PostgreSQL-backed faculty vacancy search over published vacancies.

    Supports keyword, department, qualification, designation, specialization,
    location, experience, salary and employment-type filtering plus sorting.
    Pagination is applied by the caller. No external search engine is used.
    """

    model = FacultyVacancy

    def search(
        self,
        *,
        query: str = "",
        department: str = "",
        qualification: str = "",
        designation: str = "",
        specialization: str = "",
        location: str = "",
        employment_type: str = "",
        work_type: str = "",
        experience: int | None = None,
        salary_min=None,
        salary_max=None,
        sort: str = "recent",
    ):
        now = timezone.now()
        qs = (
            self.filter_by(status=VacancyStatus.PUBLISHED)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .select_related("college")
        )

        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(vacancy_code__icontains=query)
                | Q(college_name_snapshot__icontains=query)
            )
        if department:
            qs = qs.filter(department__icontains=department)
        if qualification:
            qs = qs.filter(
                Q(minimum_qualification=qualification)
                | Q(preferred_qualification=qualification)
                | Q(qualification_required__icontains=qualification)
            )
        if designation:
            qs = qs.filter(designation=designation)
        if specialization:
            qs = qs.filter(specialization_required__icontains=specialization)
        if location:
            qs = qs.filter(
                Q(city__icontains=location)
                | Q(district__icontains=location)
                | Q(state__icontains=location)
                | Q(country__icontains=location)
                | Q(campus__icontains=location)
            )
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        if work_type:
            qs = qs.filter(work_type=work_type)
        if experience is not None:
            qs = qs.filter(
                Q(experience_min__lte=experience) | Q(experience_min__isnull=True),
            ).filter(
                Q(experience_max__gte=experience) | Q(experience_max__isnull=True),
            )

        salary_min = _to_decimal(salary_min)
        salary_max = _to_decimal(salary_max)
        if salary_min is not None:
            qs = qs.filter(Q(salary_max__gte=salary_min) | Q(salary_max__isnull=True))
        if salary_max is not None:
            qs = qs.filter(Q(salary_min__lte=salary_max) | Q(salary_min__isnull=True))

        order = _SORT_MAP.get(sort, "-published_at")
        return qs.order_by(order, "-created_at")
