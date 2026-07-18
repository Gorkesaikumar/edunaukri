"""Recruiter analytics and reporting portal."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count

from apps.applications.constants.enums import JobApplicationStatus
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.recruiter_dashboard_analytics_service import (
    RecruiterDashboardAnalyticsService,
)
from apps.it_recruitment.services.recruiter_dashboard_kpi_service import (
    RecruiterDashboardKPIService,
)
from apps.jobs.constants.enums import JobStatus
from apps.jobs.selectors.job_selector import JobPostingSelector


@dataclass
class RecruiterAnalyticsPortalContext:
    stats: list[dict]
    reporting: dict
    funnel: list[dict]
    job_performance: list[dict]
    candidate_sources: dict
    response_rate: int


class RecruiterAnalyticsPortalService(BaseService):
    def build(self, profile: RecruiterProfile) -> RecruiterAnalyticsPortalContext:
        analytics = RecruiterDashboardAnalyticsService()
        kpi = RecruiterDashboardKPIService()
        apps = kpi.applications_qs(profile)
        by_status = dict(
            apps.values("status").annotate(c=Count("id")).values_list("status", "c")
        )
        total = apps.count() or 1

        funnel = [
            {
                "label": "Applied",
                "value": by_status.get(JobApplicationStatus.APPLIED, 0),
                "pct": 100,
            },
            {
                "label": "Under Review",
                "value": by_status.get(JobApplicationStatus.UNDER_REVIEW, 0),
                "pct": round(
                    (by_status.get(JobApplicationStatus.UNDER_REVIEW, 0) / total) * 100
                ),
            },
            {
                "label": "Shortlisted",
                "value": by_status.get(JobApplicationStatus.SHORTLISTED, 0),
                "pct": round(
                    (by_status.get(JobApplicationStatus.SHORTLISTED, 0) / total) * 100
                ),
            },
            {
                "label": "Interview",
                "value": by_status.get(JobApplicationStatus.INTERVIEW_SCHEDULED, 0)
                + by_status.get(JobApplicationStatus.INTERVIEW_COMPLETED, 0),
                "pct": round(
                    (
                        by_status.get(JobApplicationStatus.INTERVIEW_SCHEDULED, 0)
                        + by_status.get(JobApplicationStatus.INTERVIEW_COMPLETED, 0)
                    )
                    / total
                    * 100
                ),
            },
            {
                "label": "Offers",
                "value": by_status.get(JobApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(JobApplicationStatus.OFFER_ACCEPTED, 0),
                "pct": round(
                    (
                        by_status.get(JobApplicationStatus.OFFER_RELEASED, 0)
                        + by_status.get(JobApplicationStatus.OFFER_ACCEPTED, 0)
                    )
                    / total
                    * 100
                ),
            },
            {
                "label": "Hired",
                "value": by_status.get(JobApplicationStatus.HIRED, 0),
                "pct": round(
                    (by_status.get(JobApplicationStatus.HIRED, 0) / total) * 100
                ),
            },
        ]

        jobs = (
            JobPostingSelector()
            .for_recruiter(profile)
            .filter(status=JobStatus.PUBLISHED)
            .order_by("-application_count")[:6]
        )
        job_performance = [
            {
                "id": str(job.pk),
                "title": job.title,
                "applications": job.application_count,
                "views": job.view_count,
                "status": job.status,
            }
            for job in jobs
        ]

        reviewed = apps.exclude(status=JobApplicationStatus.APPLIED).count()
        response_rate = round((reviewed / total) * 100) if total else 0

        return RecruiterAnalyticsPortalContext(
            stats=analytics.build_analytics_stat_cards(profile),
            reporting=analytics.build_reporting_metrics(profile),
            funnel=funnel,
            job_performance=job_performance,
            candidate_sources=kpi.candidate_sources(profile),
            response_rate=response_rate,
        )
