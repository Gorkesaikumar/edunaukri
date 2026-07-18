"""Dynamic hero insights and company branding for the recruiter dashboard."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.constants.enums import CompanySize
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    initials_from_name,
    media_url,
)
from apps.it_recruitment.services.recruiter_dashboard_kpi_service import (
    RecruiterDashboardKPIService,
)
from apps.jobs.constants.enums import JobStatus


class RecruiterDashboardHeroService(BaseService):
    """Build recruiter-specific hero copy and company card data."""

    def __init__(self):
        self._kpi = RecruiterDashboardKPIService()

    def build(self, profile: RecruiterProfile, *, company) -> dict:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        insight = self._build_insight(profile)
        return {
            "recruiter_name": profile.full_name or user.email.split("@")[0],
            "insight": insight["text"],
            "insight_key": insight["key"],
            "company_card": self._company_card(company, pu),
            "urls": {
                "company_profile": pu("recruiter_profile"),
                "post_job": pu("recruiter_job_create"),
                "browse_candidates": pu("recruiter_candidate_marketplace"),
            },
        }

    def _build_insight(self, profile: RecruiterProfile) -> dict:
        interviews_today = self._kpi.interviews_today_count(profile)
        if interviews_today:
            plural = "interview" if interviews_today == 1 else "interviews"
            return {
                "key": "interviews_today",
                "text": f"You have {interviews_today} {plural} scheduled today.",
            }

        apps = self._kpi.applications_qs(profile)
        week_start = timezone.now() - timedelta(days=7)
        new_week = apps.filter(applied_at__gte=week_start).count()
        if new_week:
            plural = "application" if new_week == 1 else "applications"
            return {
                "key": "new_apps_week",
                "text": f"You have received {new_week} new {plural} this week.",
            }

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = apps.filter(applied_at__gte=today_start).count()
        if new_today:
            plural = "application" if new_today == 1 else "applications"
            return {
                "key": "new_apps_today",
                "text": f"You received {new_today} new {plural} today. Let's find your next star hire.",
            }

        active_jobs = (
            self._kpi.jobs_qs(profile).filter(status=JobStatus.PUBLISHED).count()
        )
        if active_jobs:
            label = "opening" if active_jobs == 1 else "openings"
            return {
                "key": "active_jobs",
                "text": f"You currently have {active_jobs} active job {label}.",
            }

        if self._kpi.jobs_qs(profile).exists():
            return {
                "key": "pipeline",
                "text": "Review your pipeline and keep momentum on open roles.",
            }

        return {
            "key": "no_jobs",
            "text": "Create your first job posting to start receiving applications.",
        }

    @staticmethod
    def _company_card(company, pu) -> dict | None:
        if not company:
            return None
        size_label = ""
        if company.company_size:
            try:
                size_label = CompanySize(company.company_size).label
            except ValueError:
                size_label = company.company_size.replace("_", " ").title()
        hq = (company.headquarters_location or company.city or "").strip()
        return {
            "name": company.name,
            "initials": initials_from_name(company.name, "CO"),
            "logo_url": media_url(company.logo_file) if company.logo_file_id else None,
            "verified": company.is_verified,
            "industry": (company.industry or "").strip(),
            "size_label": size_label,
            "headquarters": hq,
            "profile_url": pu("recruiter_profile"),
        }
