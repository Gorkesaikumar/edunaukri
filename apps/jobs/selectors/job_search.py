from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from apps.core.selectors.read import ReadSelector
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting


def _to_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


_SORT_MAP = {
    "recent": "-published_at",
    "oldest": "published_at",
    "salary_high": "-salary_max",
    "salary_low": "salary_min",
    "title": "title",
}


class JobSearchSelector(ReadSelector):
    """PostgreSQL-backed job search over published jobs.

    Supports keyword, location, skills, experience, salary, employment-type and
    work-mode filtering plus sorting. Pagination is applied by the caller via
    ``paginate_envelope``. No external search engine is used.
    """

    model = JobPosting

    def search(
        self,
        *,
        query: str = "",
        location: str = "",
        employment_type: str = "",
        work_mode: str = "",
        is_remote: bool | None = None,
        skills=None,
        experience: int | None = None,
        salary_min=None,
        salary_max=None,
        sort: str = "recent",
    ):
        now = timezone.now()
        qs = (
            self.filter_by(status=JobStatus.PUBLISHED)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .select_related("company")
            .prefetch_related("required_skills__skill")
        )

        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(job_code__icontains=query)
                | Q(company_name_snapshot__icontains=query)
            )
        if location:
            qs = qs.filter(
                Q(location__icontains=location)
                | Q(city__icontains=location)
                | Q(state__icontains=location)
                | Q(country__icontains=location)
            )
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        if work_mode:
            qs = qs.filter(work_mode=work_mode)
        if is_remote is not None:
            qs = qs.filter(is_remote=is_remote)
        if skills:
            qs = qs.filter(
                required_skills__skill__name__in=skills,
                required_skills__is_deleted=False,
            ).distinct()
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
