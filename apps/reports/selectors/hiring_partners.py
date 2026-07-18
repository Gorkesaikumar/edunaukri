"""Unified "Trusted Hiring Partners" feed for the public landing page.

Showcases verified organisations from BOTH recruitment domains that are
currently hiring: IT companies (IT domain) and colleges/universities
(faculty domain). All data is database-driven.

Query strategy (N+1 safe):
- One query per domain, filtered to verified + active organisations.
- Live active-job counts via a single conditional ``Count`` annotation.
- Latest openings preloaded with a bounded ``Prefetch`` (one extra query per
  domain) into ``to_attr`` lists, then sliced in Python for the preview.
- Organisation logo + cover banner joined via ``select_related``.
"""

from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from apps.colleges.models import College
from apps.companies.models import Company
from apps.faculty.constants.enums import VacancyStatus, VacancyVisibility
from apps.faculty.models import FacultyVacancy
from apps.jobs.constants.enums import JobStatus, JobVisibility
from apps.jobs.models import JobPosting

DEFAULT_LIMIT = 12
PREVIEW_COUNT = 3

# Institution types presented under the "Universities" quick filter.
_UNIVERSITY_TYPES = {"university", "deemed_university"}


class HiringPartnersSelector:
    """Read-side builder for the verified-recruiters-hiring-now feed."""

    def active_partners(self, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
        companies = [self._map_company(c) for c in self._company_queryset(limit)]
        colleges = [self._map_college(c) for c in self._college_queryset(limit)]

        merged = companies + colleges
        # Smart sort: featured employers first, then most open jobs, then newest.
        merged.sort(key=lambda item: item["_sort_key"], reverse=True)
        return merged[:limit]

    def filter_groups(self, partners: list[dict]) -> list[dict]:
        """Distinct, order-preserving quick-filter chips present in the feed."""
        seen: dict[str, str] = {}
        for item in partners:
            seen.setdefault(item["filter_group"], item["filter_label"])
        order = ["it-company", "university", "college"]
        chips = [{"slug": "all", "label": "All"}]
        for slug in order:
            if slug in seen:
                chips.append({"slug": slug, "label": seen[slug]})
        # Any groups not covered by the canonical order (future-proofing).
        for slug, label in seen.items():
            if slug not in order:
                chips.append({"slug": slug, "label": label})
        return chips

    # ------------------------------------------------------------------ #
    # Querysets
    # ------------------------------------------------------------------ #
    def _active_job_q(self, now):
        not_expired = Q(job_postings__expires_at__isnull=True) | Q(
            job_postings__expires_at__gt=now
        )
        return (
            Q(
                job_postings__is_deleted=False,
                job_postings__status=JobStatus.PUBLISHED,
                job_postings__visibility=JobVisibility.PUBLIC,
            )
            & not_expired
        )

    def _active_vacancy_q(self, now):
        not_expired = Q(vacancies__expires_at__isnull=True) | Q(
            vacancies__expires_at__gt=now
        )
        return (
            Q(
                vacancies__is_deleted=False,
                vacancies__status=VacancyStatus.PUBLISHED,
                vacancies__visibility=VacancyVisibility.PUBLIC,
            )
            & not_expired
        )

    def _company_queryset(self, limit):
        now = timezone.now()
        not_expired = Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        active_jobs = (
            JobPosting.objects.filter(
                is_deleted=False,
                status=JobStatus.PUBLISHED,
                visibility=JobVisibility.PUBLIC,
            )
            .filter(not_expired)
            .order_by("-published_at", "-created_at")
        )

        return (
            Company.objects.filter(
                is_deleted=False,
                is_active=True,
            )
            .annotate(
                active_job_count=Count(
                    "job_postings", filter=self._active_job_q(now), distinct=True
                )
            )
            .filter(active_job_count__gt=0)
            .select_related("logo_file", "cover_banner_file")
            .prefetch_related(
                Prefetch(
                    "job_postings", queryset=active_jobs, to_attr="active_jobs_list"
                )
            )
            .order_by("-active_job_count", "-created_at")[:limit]
        )

    def _college_queryset(self, limit):
        now = timezone.now()
        not_expired = Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        active_vacancies = (
            FacultyVacancy.objects.filter(
                is_deleted=False,
                status=VacancyStatus.PUBLISHED,
                visibility=VacancyVisibility.PUBLIC,
            )
            .filter(not_expired)
            .order_by("-published_at", "-created_at")
        )

        return (
            College.objects.filter(
                is_deleted=False,
                is_active=True,
            )
            .annotate(
                active_job_count=Count(
                    "vacancies", filter=self._active_vacancy_q(now), distinct=True
                )
            )
            .filter(active_job_count__gt=0)
            .select_related("logo_file", "cover_banner_file")
            .prefetch_related(
                Prefetch(
                    "vacancies",
                    queryset=active_vacancies,
                    to_attr="active_vacancies_list",
                )
            )
            .order_by("-active_job_count", "-created_at")[:limit]
        )

    # ------------------------------------------------------------------ #
    # Mappers
    # ------------------------------------------------------------------ #
    def _map_company(self, company) -> dict:
        jobs = getattr(company, "active_jobs_list", [])
        count = company.active_job_count
        is_featured = any(getattr(j, "is_featured", False) for j in jobs)
        is_urgent = any(getattr(j, "is_urgent", False) for j in jobs)
        type_label = (
            company.get_organization_type_display()
            if company.organization_type
            else "IT Company"
        )
        return {
            "domain": "it",
            "name": company.name,
            "verified": True,
            "type_label": type_label,
            "filter_group": "it-company",
            "filter_label": "IT Companies",
            "city": company.city,
            "state": company.state,
            "location_display": self._location(company.city, company.state),
            "active_jobs": count,
            "jobs_count_label": f"{count} IT Opening{'s' if count != 1 else ''}",
            **self._hiring_status(is_featured, is_urgent),
            "active_since": self._year(company.created_at),
            "logo_url": self._file_url(company.logo_file),
            "banner_url": self._file_url(company.cover_banner_file),
            "initial": (company.name[:1] or "E").upper(),
            "preview_jobs": [j.title for j in jobs[:PREVIEW_COUNT]],
            "more_count": max(count - PREVIEW_COUNT, 0),
            "profile_url": reverse("institution_detail", kwargs={"slug": company.slug}),
            "is_featured": is_featured,
            "_sort_key": (is_featured, count, company.created_at),
        }

    def _map_college(self, college) -> dict:
        vacancies = getattr(college, "active_vacancies_list", [])
        count = college.active_job_count
        is_featured = any(getattr(v, "is_featured", False) for v in vacancies)
        is_urgent = any(getattr(v, "is_urgent", False) for v in vacancies)
        institution_type = college.institution_type
        type_label = (
            college.get_institution_type_display() if institution_type else "College"
        )
        if institution_type in _UNIVERSITY_TYPES:
            filter_group, filter_label = "university", "Universities"
        else:
            filter_group, filter_label = "college", "Colleges"
        return {
            "domain": "faculty",
            "name": college.name,
            "verified": True,
            "type_label": type_label,
            "filter_group": filter_group,
            "filter_label": filter_label,
            "city": college.city,
            "state": college.state,
            "location_display": self._location(college.city, college.state),
            "active_jobs": count,
            "jobs_count_label": f"{count} Faculty Vacanc{'y' if count == 1 else 'ies'}",
            **self._hiring_status(is_featured, is_urgent),
            "active_since": self._year(college.created_at),
            "logo_url": self._file_url(college.logo_file),
            "banner_url": self._file_url(college.cover_banner_file),
            "initial": (college.name[:1] or "E").upper(),
            "preview_jobs": [v.title for v in vacancies[:PREVIEW_COUNT]],
            "more_count": max(count - PREVIEW_COUNT, 0),
            "profile_url": reverse("institution_detail", kwargs={"slug": college.slug}),
            "is_featured": is_featured,
            "_sort_key": (is_featured, count, college.created_at),
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _hiring_status(is_featured, is_urgent) -> dict:
        if is_urgent:
            return {"hiring_status": "urgent", "hiring_label": "Urgently Hiring"}
        if is_featured:
            return {"hiring_status": "featured", "hiring_label": "Featured Employer"}
        return {"hiring_status": "now", "hiring_label": "Hiring Now"}

    @staticmethod
    def _location(city, state) -> str:
        parts = [p for p in (city, state) if p]
        return ", ".join(parts) if parts else "India"

    @staticmethod
    def _year(dt) -> int | None:
        return dt.year if dt else None

    @staticmethod
    def _file_url(stored_file) -> str | None:
        if not stored_file or not getattr(stored_file, "storage_path", ""):
            return None
        from django.conf import settings

        path = str(stored_file.storage_path).replace("\\", "/")
        if path.startswith(("http://", "https://", "/")):
            return path
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return f"{media_url}{path.lstrip('/')}"
