"""Unified "Featured Opportunities" feed for the public landing page.

Merges the newest published/approved postings from BOTH recruitment domains
(IT jobs + faculty vacancies) into a single, intelligently interleaved feed
ordered by most-recently published. All content is database-driven.

Query strategy:
- Each domain query is bounded (``LIMIT``) and uses ``select_related`` for the
  organisation + its logo file to avoid N+1 lookups.
- Applicant counts come from a denormalised counter column (no join needed).
- The two bounded result sets are merged in Python and re-sorted, then trimmed
  to the requested limit.
"""

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.faculty.constants.enums import VacancyStatus, VacancyVisibility
from apps.faculty.models import FacultyVacancy
from apps.jobs.constants.enums import JobStatus, JobVisibility
from apps.jobs.models import JobPosting

DEFAULT_LIMIT = 12


class FeaturedJobsSelector:
    """Read-side builder for the unified featured-opportunities feed."""

    def latest_unified(self, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
        now = timezone.now()
        not_expired = Q(expires_at__isnull=True) | Q(expires_at__gt=now)

        it_items = [self._map_job(job) for job in self._it_queryset(not_expired, limit)]
        faculty_items = [
            self._map_vacancy(vac) for vac in self._faculty_queryset(not_expired, limit)
        ]

        merged = it_items + faculty_items
        merged.sort(key=lambda item: item["_sort_key"], reverse=True)
        return merged[:limit]

    # ------------------------------------------------------------------ #
    # Querysets
    # ------------------------------------------------------------------ #
    def _it_queryset(self, not_expired, limit):
        return (
            JobPosting.objects.filter(
                is_deleted=False,
                status=JobStatus.PUBLISHED,
                visibility=JobVisibility.PUBLIC,
            )
            .filter(not_expired)
            .select_related("company", "company__logo_file")
            .order_by("-published_at", "-created_at")[:limit]
        )

    def _faculty_queryset(self, not_expired, limit):
        return (
            FacultyVacancy.objects.filter(
                is_deleted=False,
                status=VacancyStatus.PUBLISHED,
                visibility=VacancyVisibility.PUBLIC,
            )
            .filter(not_expired)
            .select_related("college", "college__logo_file")
            .order_by("-published_at", "-created_at")[:limit]
        )

    # ------------------------------------------------------------------ #
    # Mappers -> normalised card DTO
    # ------------------------------------------------------------------ #
    def _map_job(self, job) -> dict:
        company = job.company
        org_name = job.company_name_snapshot or (company.name if company else "")
        location = self._location(
            city=job.city, state=job.state, remote=job.is_remote, fallback=job.location
        )
        category = ""
        if company and company.organization_type:
            category = company.get_organization_type_display()
        return {
            "domain": "it",
            "domain_label": "IT Domain",
            "domain_icon": "bi-code-slash",
            "title": job.title,
            "org_name": org_name,
            "logo_url": self._logo_url(company.logo_file if company else None),
            "initial": (org_name[:1] or "E").upper(),
            "salary_display": self._salary(
                job.salary_min, job.salary_max, job.salary_visibility
            ),
            "work_label": job.get_work_mode_display(),
            "experience_label": self._experience(job.experience_min),
            "category_label": category or "IT",
            "location": location,
            "posted_display": self._posted(job.published_at or job.created_at),
            "applicant_count": job.application_count,
            "detail_url": reverse("marketplace_job_detail", kwargs={"job_id": job.pk}),
            "job_id": str(job.pk),
            "_sort_key": job.published_at or job.created_at,
        }

    def _map_vacancy(self, vac) -> dict:
        college = vac.college
        org_name = vac.college_name_snapshot or (college.name if college else "")
        location = self._location(
            city=vac.city, state=vac.state, remote=False, fallback=vac.campus
        )
        category = ""
        if vac.designation:
            category = vac.get_designation_display()
        elif college and college.institution_type:
            category = college.get_institution_type_display()
        return {
            "domain": "faculty",
            "domain_label": "Faculty Domain",
            "domain_icon": "bi-mortarboard",
            "title": vac.title,
            "org_name": org_name,
            "logo_url": self._logo_url(college.logo_file if college else None),
            "initial": (org_name[:1] or "E").upper(),
            "salary_display": self._salary(
                vac.salary_min, vac.salary_max, vac.salary_visibility
            ),
            "work_label": vac.get_work_type_display(),
            "experience_label": self._experience(vac.experience_min),
            "category_label": category or "Faculty",
            "location": location,
            "posted_display": self._posted(vac.published_at or vac.created_at),
            "applicant_count": vac.application_count,
            "detail_url": reverse(
                "marketplace_vacancy_detail", kwargs={"job_id": vac.pk}
            ),
            "_sort_key": vac.published_at or vac.created_at,
        }

    # ------------------------------------------------------------------ #
    # Formatting helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _trim(number: float) -> str:
        text = f"{number:.1f}"
        return text[:-2] if text.endswith(".0") else text

    def _salary(self, smin, smax, visibility) -> str | None:
        if visibility and str(visibility) != "visible":
            return None
        if not smin and not smax:
            return None

        def unit(value) -> str:
            value = float(value)
            if value >= 10_000_000:  # 1 crore
                return f"{self._trim(value / 10_000_000)}Cr"
            return f"{self._trim(value / 100_000)}L"

        low = smin or smax
        high = smax or smin
        if low == high:
            return f"\u20b9{unit(low)} PA"
        return f"\u20b9{unit(low)} - {unit(high)} PA"

    @staticmethod
    def _experience(experience_min) -> str | None:
        if experience_min is None:
            return None
        return f"{experience_min}+ Yrs Exp"

    @staticmethod
    def _location(*, city, state, remote, fallback) -> str:
        if remote:
            return "Remote"
        return city or fallback or state or "India"

    @staticmethod
    def _posted(dt) -> str:
        if not dt:
            return "Recently Posted"
        delta = timezone.now() - dt
        days = delta.days
        if days <= 0:
            hours = delta.seconds // 3600
            if hours <= 0:
                minutes = delta.seconds // 60
                if minutes <= 1:
                    return "Posted Just Now"
                return f"Posted {minutes} Mins Ago"
            return f"Posted {hours} Hour{'s' if hours > 1 else ''} Ago"
        if days == 1:
            return "Posted 1 Day Ago"
        if days < 30:
            return f"Posted {days} Days Ago"
        months = days // 30
        if months == 1:
            return "Posted 1 Month Ago"
        return f"Posted {months} Months Ago"

    @staticmethod
    def _logo_url(stored_file) -> str | None:
        if not stored_file or not getattr(stored_file, "storage_path", ""):
            return None
        path = str(stored_file.storage_path).replace("\\", "/")
        if path.startswith(("http://", "https://", "/")):
            return path
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return f"{media_url}{path.lstrip('/')}"
