"""Aggregate dashboard data for the IT Recruiter portal."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import greeting_for_hour
from apps.it_recruitment.services.recruiter_dashboard_hero_service import (
    RecruiterDashboardHeroService,
)
from apps.it_recruitment.services.recruiter_dashboard_kpi_service import (
    RecruiterDashboardKPIService,
)
from apps.it_recruitment.services.recruiter_dashboard_widgets_service import (
    DashboardFilters,
    RecruiterDashboardWidgetsService,
)


@dataclass
class RecruiterDashboardContext:
    greeting: str
    recruiter_name: str
    display_name: str
    company_name: str
    company_verified: bool
    welcome_message: str
    hero_insight: str
    hero_insight_key: str
    company_card: dict | None
    new_applications_today: int
    stats: list[dict]
    pipeline: list[dict]
    active_jobs: list[dict]
    upcoming_interviews: list[dict]
    interviews_today: int
    candidate_sources: dict
    recent_applications: list[dict]
    recent_activity: list[dict]
    notifications: list[dict]
    analytics: dict
    filter_options: dict
    filters: dict
    api_urls: dict
    urls: dict = field(default_factory=dict)


class RecruiterDashboardService(BaseService):
    def __init__(self):
        self.kpi = RecruiterDashboardKPIService()
        self.widgets = RecruiterDashboardWidgetsService()

    def build(
        self,
        profile: RecruiterProfile,
        *,
        filters: DashboardFilters | None = None,
    ) -> RecruiterDashboardContext:
        filters = filters or DashboardFilters()
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        company = self._primary_company(profile)
        company_name = company.name if company else profile.full_name
        hero = RecruiterDashboardHeroService().build(profile, company=company)
        apps_qs = self.widgets._filtered_apps(profile, filters)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = apps_qs.filter(applied_at__gte=today_start).count()
        widget_data = self.widgets.build_all(profile, filters=filters)

        return RecruiterDashboardContext(
            greeting=greeting_for_hour(timezone.localtime().hour),
            recruiter_name=hero["recruiter_name"],
            display_name=company_name,
            company_name=company_name,
            company_verified=bool(company and company.is_verified),
            welcome_message=hero["insight"],
            hero_insight=hero["insight"],
            hero_insight_key=hero["insight_key"],
            company_card=hero["company_card"],
            new_applications_today=new_today,
            stats=self.kpi.build_stats(profile),
            pipeline=widget_data["pipeline"],
            active_jobs=widget_data["active_jobs"],
            upcoming_interviews=widget_data["upcoming_interviews"],
            interviews_today=self.kpi.interviews_today_count(profile),
            candidate_sources=widget_data["candidate_sources"],
            recent_applications=self._recent_applications(apps_qs, pu),
            recent_activity=widget_data["recent_activity"],
            notifications=widget_data["notifications"],
            analytics=widget_data["analytics"],
            filter_options=widget_data["filter_options"],
            filters=widget_data["filters"],
            api_urls=widget_data["api_urls"],
            urls={
                "post_job": hero["urls"]["post_job"],
                "browse_candidates": hero["urls"]["browse_candidates"],
                "company_profile": hero["urls"]["company_profile"],
                "pipeline": pu("recruiter_candidates"),
                "manage_jobs": pu("recruiter_jobs"),
                "interviews": pu("recruiter_interviews"),
                "analytics": pu("recruiter_analytics"),
                "notifications": pu("recruiter_notifications"),
                "settings": pu("recruiter_settings"),
            },
        )

    @staticmethod
    def _primary_company(profile: RecruiterProfile):
        membership = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .select_related("company", "company__logo_file")
            .order_by("-is_primary", "-created_at")
            .first()
        )
        return membership.company if membership else None

    def _recent_applications(self, apps_qs, pu) -> list[dict]:
        from apps.applications.constants.enums import JobApplicationStatus

        status_labels = dict(JobApplicationStatus.choices)
        rows = apps_qs.order_by("-applied_at")[:8]
        items = []
        for app in rows:
            items.append(
                {
                    "id": str(app.pk),
                    "candidate": app.applicant_name_snapshot,
                    "job_title": app.job_title_snapshot,
                    "company": app.company_name_snapshot,
                    "status": app.status,
                    "status_label": status_labels.get(
                        app.status, app.status.replace("_", " ").title()
                    ),
                    "applied_label": timezone.localtime(app.applied_at).strftime(
                        "%b %d, %Y"
                    ),
                    "url": pu("recruiter_candidates"),
                }
            )
        return items
