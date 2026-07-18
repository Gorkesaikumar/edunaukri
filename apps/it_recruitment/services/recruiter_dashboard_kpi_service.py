"""Live KPI and trend calculations for the IT Recruiter dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.applications.constants.enums import ApplicationSource
from apps.applications.models import JobApplication
from apps.applications.models.interview import JobApplicationInterview
from apps.applications.constants.interview_enums import InterviewStatus
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.models import JobPosting
from apps.it_recruitment.services.recruiter_dashboard_analytics_service import (
    RecruiterDashboardAnalyticsService,
)


@dataclass
class RecruiterTrendIndicator:
    label: str
    tone: str = "secondary"

    def to_dict(self) -> dict:
        return {"label": self.label, "tone": self.tone}


class RecruiterDashboardKPIService(BaseService):
    """Compute recruiter dashboard metrics with period-over-period trends."""

    def __init__(self):
        self._now = timezone.now()
        self._week_start = self._now - timedelta(days=7)
        self._prev_week_start = self._now - timedelta(days=14)
        self._today_start = self._now.replace(hour=0, minute=0, second=0, microsecond=0)

    def applications_qs(self, recruiter: RecruiterProfile) -> QuerySet:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        return JobApplication.objects.filter(
            job_posting__company_id__in=company_ids,
            is_deleted=False,
        )

    def jobs_qs(self, recruiter: RecruiterProfile) -> QuerySet:
        return JobPosting.objects.filter(posted_by=recruiter, is_deleted=False)

    def trend_for_count(self, current: int, previous: int) -> RecruiterTrendIndicator:
        if previous == 0:
            if current == 0:
                return RecruiterTrendIndicator("0%", "muted")
            return RecruiterTrendIndicator("+100%", "secondary")
        change = round(((current - previous) / previous) * 100)
        if change > 0:
            return RecruiterTrendIndicator(f"+{change}%", "secondary")
        if change < 0:
            return RecruiterTrendIndicator(f"{change}%", "primary")
        return RecruiterTrendIndicator("0%", "muted")

    def count_trend(
        self, qs: QuerySet, date_field: str = "applied_at"
    ) -> RecruiterTrendIndicator:
        current = qs.filter(**{f"{date_field}__gte": self._week_start}).count()
        previous = qs.filter(
            **{
                f"{date_field}__gte": self._prev_week_start,
                f"{date_field}__lt": self._week_start,
            }
        ).count()
        return self.trend_for_count(current, previous)

    def build_stats(self, recruiter: RecruiterProfile) -> list[dict]:
        return RecruiterDashboardAnalyticsService().build_stat_cards(recruiter)

    def candidate_sources(self, recruiter: RecruiterProfile) -> dict:
        apps = self.applications_qs(recruiter)
        total = apps.count()
        if total == 0:
            return {
                "total": 0,
                "segments": [
                    {
                        "label": "EduNaukri Portal",
                        "key": "portal",
                        "pct": 0,
                        "tone": "primary",
                    },
                    {
                        "label": "Direct Referrals",
                        "key": "referral",
                        "pct": 0,
                        "tone": "secondary",
                    },
                    {
                        "label": "Other Channels",
                        "key": "other",
                        "pct": 0,
                        "tone": "muted",
                    },
                ],
            }

        portal_sources = {
            ApplicationSource.DIRECT,
            ApplicationSource.JOB_BOARD,
            ApplicationSource.INTERNAL,
            "",
        }
        referral_sources = {ApplicationSource.REFERRAL, ApplicationSource.AGENCY}

        portal = apps.filter(Q(source__in=portal_sources) | Q(source="")).count()
        referral = apps.filter(source__in=referral_sources).count()
        other = max(0, total - portal - referral)

        def pct(n: int) -> int:
            return round((n / total) * 100)

        portal_pct = pct(portal)
        referral_pct = pct(referral)
        other_pct = max(0, 100 - portal_pct - referral_pct)

        return {
            "total": total,
            "segments": [
                {
                    "label": "EduNaukri Portal",
                    "key": "portal",
                    "pct": portal_pct,
                    "tone": "primary",
                    "count": portal,
                },
                {
                    "label": "Direct Referrals",
                    "key": "referral",
                    "pct": referral_pct,
                    "tone": "secondary",
                    "count": referral,
                },
                {
                    "label": "Other Channels",
                    "key": "other",
                    "pct": other_pct,
                    "tone": "muted",
                    "count": other,
                },
            ],
        }

    def upcoming_interviews(
        self, recruiter: RecruiterProfile, *, limit: int = 5
    ) -> list[JobApplicationInterview]:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        return list(
            JobApplicationInterview.objects.filter(
                application__job_posting__company_id__in=company_ids,
                application__is_deleted=False,
                is_deleted=False,
                scheduled_at__gte=self._today_start - timedelta(hours=2),
                status__in=(
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.IN_PROGRESS,
                ),
            )
            .select_related("application", "application__job_seeker")
            .order_by("scheduled_at")[:limit]
        )

    def interviews_today_count(self, recruiter: RecruiterProfile) -> int:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        tomorrow = self._today_start + timedelta(days=1)
        return JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
            scheduled_at__gte=self._today_start,
            scheduled_at__lt=tomorrow,
            status__in=(
                InterviewStatus.SCHEDULED,
                InterviewStatus.CONFIRMED,
                InterviewStatus.IN_PROGRESS,
                InterviewStatus.COMPLETED,
            ),
        ).count()
