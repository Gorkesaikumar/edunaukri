from django.db.models import Q
from django.utils import timezone

from apps.core.selectors.read import ReadSelector
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting

_SKILL_PREFETCH = "required_skills__skill"


def _not_expired(queryset):
    """Exclude published jobs whose expiry date has passed (read-time expiry)."""
    now = timezone.now()
    return queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


class JobPostingSelector(ReadSelector):
    model = JobPosting
    search_fields = ("title", "location", "company_name_snapshot", "job_code")

    def get_or_none(self, job_id):
        return (
            self.filter_by(pk=job_id)
            .select_related("company")
            .prefetch_related(_SKILL_PREFETCH)
            .first()
        )

    def published(self, *, search: str | None = None):
        queryset = _not_expired(self.filter_by(status=JobStatus.PUBLISHED)).select_related(
            "company"
        ).prefetch_related(_SKILL_PREFETCH)
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.order_by("-published_at")

    def get_published_by_id(self, job_id):
        return _not_expired(
            self.filter_by(pk=job_id, status=JobStatus.PUBLISHED)
        ).first()

    def for_recruiter(self, recruiter):
        from apps.companies.selectors.company_selector import CompanyMemberSelector

        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        return (
            self.filter_by(company_id__in=company_ids)
            .select_related("company")
            .prefetch_related(_SKILL_PREFETCH)
            .order_by("-created_at")
        )

    def for_company(self, company_id):
        return self.filter_by(company_id=company_id).select_related("company").order_by("-created_at")

    def admin_list(
        self, *, status: str | None = None, company_id=None, search: str | None = None
    ):
        queryset = self.filter_by().select_related("company")
        if status:
            queryset = queryset.filter(status=status)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.order_by("-created_at")


# Canonical alias exposed by the Job Management module.
JobSelector = JobPostingSelector


class RecruiterJobSelector(ReadSelector):
    """Read scope limited to jobs the recruiter's companies own."""

    model = JobPosting

    def _company_ids(self, recruiter):
        from apps.companies.selectors.company_selector import CompanyMemberSelector

        return (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )

    def for_recruiter(self, recruiter, *, status: str | None = None):
        queryset = self.filter_by(
            company_id__in=self._company_ids(recruiter)
        ).select_related("company").prefetch_related(_SKILL_PREFETCH)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def templates(self, recruiter):
        return (
            self.filter_by(
                company_id__in=self._company_ids(recruiter), is_template=True
            )
            .prefetch_related(_SKILL_PREFETCH)
            .order_by("-created_at")
        )


class CompanyJobSelector(ReadSelector):
    """Read scope limited to a single company's jobs."""

    model = JobPosting

    def for_company(self, company_id, *, status: str | None = None):
        queryset = self.filter_by(company_id=company_id).select_related("company").prefetch_related(
            _SKILL_PREFETCH
        )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def published_for_company(self, company_id):
        return self.for_company(company_id, status=JobStatus.PUBLISHED)


class PublicJobSelector(ReadSelector):
    """Read scope for anonymous / job-seeker discovery of published jobs."""

    model = JobPosting

    def published(self):
        return (
            _not_expired(self.filter_by(status=JobStatus.PUBLISHED))
            .select_related("company")
            .prefetch_related(_SKILL_PREFETCH)
            .order_by("-published_at")
        )

    def get_published(self, job_id):
        return (
            _not_expired(self.filter_by(pk=job_id, status=JobStatus.PUBLISHED))
            .select_related("company")
            .prefetch_related(_SKILL_PREFETCH)
            .first()
        )
