"""Dashboard stat cards — job, candidate, interview, offer, and hiring analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.interview_enums import InterviewStatus
from apps.applications.models import JobApplication
from apps.applications.models.interview import JobApplicationInterview
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting


@dataclass
class StatTrend:
    label: str
    tone: str  # up | down | muted

    def to_dict(self) -> dict:
        return {"label": self.label, "tone": self.tone}


def format_stat_value(value: int) -> str:
    """Enterprise formatting — no leading zeros."""
    return str(max(0, int(value)))


class JobAnalyticsService(BaseService):
    def metrics(
        self, recruiter: RecruiterProfile, *, now, week_start, prev_week_start
    ) -> dict:
        jobs = JobPosting.objects.filter(posted_by=recruiter, is_deleted=False)
        active = jobs.filter(status=JobStatus.PUBLISHED)
        active_count = active.count()
        published_this_week = active.filter(published_at__gte=week_start).count()
        published_prev_week = active.filter(
            published_at__gte=prev_week_start, published_at__lt=week_start
        ).count()

        if active_count == 0:
            subtitle = "No active jobs"
        elif published_this_week:
            subtitle = f"{published_this_week} newly published this week"
        else:
            subtitle = f"{active_count} open {'role' if active_count == 1 else 'roles'}"

        return {
            "key": "active_jobs",
            "label": "Active Jobs",
            "value": format_stat_value(active_count),
            "icon": "work",
            "tone": "primary",
            "trend": _trend_for_count(
                published_this_week, published_prev_week
            ).to_dict(),
            "subtitle": subtitle,
        }


class CandidateAnalyticsService(BaseService):
    def new_applications_card(
        self,
        apps: QuerySet,
        *,
        today_start,
        week_start,
        prev_week_start,
    ) -> dict:
        agg = apps.aggregate(
            today=Count("id", filter=Q(applied_at__gte=today_start)),
            week=Count("id", filter=Q(applied_at__gte=week_start)),
            prev_week=Count(
                "id",
                filter=Q(applied_at__gte=prev_week_start, applied_at__lt=week_start),
            ),
        )
        today = agg["today"] or 0
        week = agg["week"] or 0

        if today == 0:
            subtitle = "No applications today" if week == 0 else f"{week} this week"
        elif week > today:
            subtitle = f"{week} this week"
        else:
            subtitle = "Received today"

        return {
            "key": "new_apps",
            "label": "New Applications",
            "value": format_stat_value(today),
            "icon": "group",
            "tone": "secondary",
            "trend": _trend_for_count(week, agg["prev_week"] or 0).to_dict(),
            "subtitle": subtitle,
        }

    def shortlisted_card(
        self,
        apps: QuerySet,
        *,
        week_start,
        prev_week_start,
    ) -> dict:
        agg = apps.aggregate(
            total=Count("id", filter=Q(status=JobApplicationStatus.SHORTLISTED)),
            week=Count(
                "id",
                filter=Q(
                    status=JobApplicationStatus.SHORTLISTED, updated_at__gte=week_start
                ),
            ),
            prev_week=Count(
                "id",
                filter=Q(
                    status=JobApplicationStatus.SHORTLISTED,
                    updated_at__gte=prev_week_start,
                    updated_at__lt=week_start,
                ),
            ),
        )
        total = agg["total"] or 0
        subtitle = (
            "No shortlisted candidates" if total == 0 else f"{total} in your pipeline"
        )

        return {
            "key": "shortlisted",
            "label": "Shortlisted",
            "value": format_stat_value(total),
            "icon": "star",
            "tone": "tertiary",
            "trend": _trend_for_count(
                agg["week"] or 0, agg["prev_week"] or 0
            ).to_dict(),
            "subtitle": subtitle,
        }


class InterviewAnalyticsService(BaseService):
    def metrics(
        self,
        company_ids,
        *,
        today_start,
        week_start,
        prev_week_start,
        interviews_today: int,
    ) -> dict:
        base = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
        )
        scheduled_statuses = (
            InterviewStatus.SCHEDULED,
            InterviewStatus.CONFIRMED,
            InterviewStatus.IN_PROGRESS,
        )
        agg = base.aggregate(
            scheduled=Count("id", filter=Q(status__in=scheduled_statuses)),
            week=Count("id", filter=Q(scheduled_at__gte=week_start)),
            prev_week=Count(
                "id",
                filter=Q(
                    scheduled_at__gte=prev_week_start, scheduled_at__lt=week_start
                ),
            ),
        )
        scheduled = agg["scheduled"] or 0

        if scheduled == 0:
            subtitle = "No interviews scheduled"
        elif interviews_today:
            subtitle = f"{interviews_today} scheduled today"
        else:
            subtitle = f"{scheduled} on your calendar"

        return {
            "key": "interviews",
            "label": "Interviews",
            "value": format_stat_value(scheduled),
            "icon": "calendar_today",
            "tone": "primary",
            "trend": _trend_for_count(
                agg["week"] or 0, agg["prev_week"] or 0
            ).to_dict(),
            "subtitle": subtitle,
        }


class OfferAnalyticsService(BaseService):
    def metrics(self, apps: QuerySet, *, week_start, prev_week_start) -> dict:
        agg = apps.aggregate(
            released=Count("id", filter=Q(status=JobApplicationStatus.OFFER_RELEASED)),
            awaiting=Count("id", filter=Q(status=JobApplicationStatus.OFFER_RELEASED)),
            accepted=Count("id", filter=Q(status=JobApplicationStatus.OFFER_ACCEPTED)),
            week=Count(
                "id",
                filter=Q(
                    status=JobApplicationStatus.OFFER_RELEASED,
                    updated_at__gte=week_start,
                ),
            ),
            prev_week=Count(
                "id",
                filter=Q(
                    status=JobApplicationStatus.OFFER_RELEASED,
                    updated_at__gte=prev_week_start,
                    updated_at__lt=week_start,
                ),
            ),
        )
        released = (agg["released"] or 0) + (agg["accepted"] or 0)
        awaiting = agg["awaiting"] or 0

        if released == 0:
            subtitle = "No offers released"
        elif awaiting:
            subtitle = f"{awaiting} awaiting candidate response"
        else:
            subtitle = f"{released} total offers"

        return {
            "key": "offers",
            "label": "Offers",
            "value": format_stat_value(released),
            "icon": "verified_user",
            "tone": "secondary",
            "trend": _trend_for_count(
                agg["week"] or 0, agg["prev_week"] or 0
            ).to_dict(),
            "subtitle": subtitle,
        }


class HiringAnalyticsService(BaseService):
    def metrics(
        self, apps: QuerySet, *, month_start, week_start, prev_week_start
    ) -> dict:
        agg = apps.aggregate(
            total=Count("id", filter=Q(status=JobApplicationStatus.HIRED)),
            month=Count(
                "id",
                filter=Q(status=JobApplicationStatus.HIRED, hired_at__gte=month_start),
            ),
            week=Count(
                "id",
                filter=Q(status=JobApplicationStatus.HIRED, hired_at__gte=week_start),
            ),
            prev_week=Count(
                "id",
                filter=Q(
                    status=JobApplicationStatus.HIRED,
                    hired_at__gte=prev_week_start,
                    hired_at__lt=week_start,
                ),
            ),
        )
        total = agg["total"] or 0
        month_count = agg["month"] or 0

        if total == 0:
            subtitle = "No hires yet"
        elif month_count:
            subtitle = f"{month_count} this month"
        else:
            subtitle = f"{total} total hires"

        return {
            "key": "hired",
            "label": "Hired",
            "value": format_stat_value(total),
            "icon": "person_add",
            "tone": "tertiary",
            "trend": _trend_for_count(
                agg["week"] or 0, agg["prev_week"] or 0
            ).to_dict(),
            "subtitle": subtitle,
        }


def _trend_for_count(
    current: int, previous: int, *, period: str = "last week"
) -> StatTrend:
    if previous == 0:
        if current == 0:
            return StatTrend("No Change", "muted")
        return StatTrend(f"▲ +100% from {period}", "up")
    change = round(((current - previous) / previous) * 100)
    if change > 0:
        return StatTrend(f"▲ +{change}% from {period}", "up")
    if change < 0:
        return StatTrend(f"▼ {change}% from {period}", "down")
    return StatTrend("No Change", "muted")


class RecruiterDashboardAnalyticsService(BaseService):
    """Build live dashboard stat cards for the recruiter portal."""

    def _time_windows(self):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)
        month_start = today_start.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        return (
            now,
            today_start,
            week_start,
            prev_week_start,
            month_start,
            prev_month_start,
        )

    def _base_querysets(self, recruiter: RecruiterProfile):
        company_ids = list(
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        apps = JobApplication.objects.filter(
            job_posting__company_id__in=company_ids,
            is_deleted=False,
        )
        return company_ids, apps

    def build_primary_kpi_cards(self, recruiter: RecruiterProfile) -> list[dict]:
        """Executive KPI row — four high-value metrics for the dashboard."""
        _, today_start, week_start, prev_week_start, month_start, prev_month_start = (
            self._time_windows()
        )
        company_ids, apps = self._base_querysets(recruiter)

        jobs = JobPosting.objects.filter(posted_by=recruiter, is_deleted=False)
        active_count = jobs.filter(status=JobStatus.PUBLISHED).count()
        published_this_week = jobs.filter(
            status=JobStatus.PUBLISHED, published_at__gte=week_start
        ).count()
        published_prev_week = jobs.filter(
            status=JobStatus.PUBLISHED,
            published_at__gte=prev_week_start,
            published_at__lt=week_start,
        ).count()

        app_agg = apps.aggregate(
            today=Count("id", filter=Q(applied_at__gte=today_start)),
            week=Count("id", filter=Q(applied_at__gte=week_start)),
            prev_week=Count(
                "id",
                filter=Q(applied_at__gte=prev_week_start, applied_at__lt=week_start),
            ),
        )
        today_apps = app_agg["today"] or 0

        interviews_today = _interviews_today_count(company_ids, today_start)
        interview_agg = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
        ).aggregate(
            week=Count("id", filter=Q(scheduled_at__gte=week_start)),
            prev_week=Count(
                "id",
                filter=Q(
                    scheduled_at__gte=prev_week_start, scheduled_at__lt=week_start
                ),
            ),
        )

        hire_agg = apps.aggregate(
            month=Count(
                "id",
                filter=Q(status=JobApplicationStatus.HIRED, hired_at__gte=month_start),
            ),
            prev_month=Count(
                "id",
                filter=Q(
                    status=JobApplicationStatus.HIRED,
                    hired_at__gte=prev_month_start,
                    hired_at__lt=month_start,
                ),
            ),
        )
        hired_month = hire_agg["month"] or 0

        if active_count == 0:
            jobs_subtitle = "No active jobs"
        else:
            jobs_subtitle = f"{published_this_week} published this week"

        if today_apps == 0:
            apps_subtitle = "No new applications today"
        else:
            apps_subtitle = "Across all active jobs"

        if interviews_today == 0:
            interviews_subtitle = "No interviews scheduled"
        else:
            interviews_subtitle = "Upcoming interviews"

        if hired_month == 0:
            hired_subtitle = "No hires this month"
        else:
            hired_subtitle = "Monthly hiring summary"

        return [
            {
                "key": "active_jobs",
                "label": "Active Jobs",
                "value": format_stat_value(active_count),
                "icon": "work",
                "tone": "primary",
                "trend": _trend_for_count(
                    published_this_week, published_prev_week
                ).to_dict(),
                "subtitle": jobs_subtitle,
            },
            {
                "key": "new_applications",
                "label": "New Applications",
                "value": format_stat_value(today_apps),
                "icon": "inbox",
                "tone": "secondary",
                "trend": _trend_for_count(
                    app_agg["week"] or 0, app_agg["prev_week"] or 0
                ).to_dict(),
                "subtitle": apps_subtitle,
            },
            {
                "key": "interviews_today",
                "label": "Interviews Today",
                "value": format_stat_value(interviews_today),
                "icon": "calendar_today",
                "tone": "primary",
                "trend": _trend_for_count(
                    interview_agg["week"] or 0, interview_agg["prev_week"] or 0
                ).to_dict(),
                "subtitle": interviews_subtitle,
            },
            {
                "key": "hired_month",
                "label": "Hired This Month",
                "value": format_stat_value(hired_month),
                "icon": "person_add",
                "tone": "tertiary",
                "trend": _trend_for_count(
                    hired_month, hire_agg["prev_month"] or 0, period="last month"
                ).to_dict(),
                "subtitle": hired_subtitle,
            },
        ]

    def build_analytics_stat_cards(self, recruiter: RecruiterProfile) -> list[dict]:
        """Extended reporting metrics for the Analytics module."""
        now, today_start, week_start, prev_week_start, month_start, prev_month_start = (
            self._time_windows()
        )
        company_ids, apps = self._base_querysets(recruiter)

        interviews_today = _interviews_today_count(company_ids, today_start)

        jobs_svc = JobAnalyticsService()
        candidate_svc = CandidateAnalyticsService()
        interview_svc = InterviewAnalyticsService()
        offer_svc = OfferAnalyticsService()
        hiring_svc = HiringAnalyticsService()

        total_apps = apps.count()
        total_candidates = apps.values("job_seeker_id").distinct().count()
        pending = apps.filter(
            status__in=(JobApplicationStatus.APPLIED, JobApplicationStatus.UNDER_REVIEW)
        ).count()
        hired_month = apps.filter(
            status=JobApplicationStatus.HIRED, hired_at__gte=month_start
        ).count()

        apps_week = apps.filter(applied_at__gte=week_start).count()
        apps_prev_week = apps.filter(
            applied_at__gte=prev_week_start, applied_at__lt=week_start
        ).count()

        candidates_week = (
            apps.filter(applied_at__gte=week_start)
            .values("job_seeker_id")
            .distinct()
            .count()
        )
        candidates_prev_week = (
            apps.filter(applied_at__gte=prev_week_start, applied_at__lt=week_start)
            .values("job_seeker_id")
            .distinct()
            .count()
        )

        pending_week = apps.filter(
            status__in=(
                JobApplicationStatus.APPLIED,
                JobApplicationStatus.UNDER_REVIEW,
            ),
            updated_at__gte=week_start,
        ).count()
        pending_prev_week = apps.filter(
            status__in=(
                JobApplicationStatus.APPLIED,
                JobApplicationStatus.UNDER_REVIEW,
            ),
            updated_at__gte=prev_week_start,
            updated_at__lt=week_start,
        ).count()

        return [
            jobs_svc.metrics(
                recruiter,
                now=now,
                week_start=week_start,
                prev_week_start=prev_week_start,
            ),
            {
                "key": "total_applications",
                "label": "Total Applications",
                "value": format_stat_value(total_apps),
                "icon": "description",
                "tone": "secondary",
                "trend": _trend_for_count(apps_week, apps_prev_week).to_dict(),
                "subtitle": f"{apps_week} this week"
                if apps_week
                else "Across all jobs",
            },
            {
                "key": "total_candidates",
                "label": "Total Candidates",
                "value": format_stat_value(total_candidates),
                "icon": "groups",
                "tone": "tertiary",
                "trend": _trend_for_count(
                    candidates_week, candidates_prev_week
                ).to_dict(),
                "subtitle": "Unique applicants",
            },
            {
                "key": "interviews_today",
                "label": "Interviews Today",
                "value": format_stat_value(interviews_today),
                "icon": "calendar_today",
                "tone": "primary",
                "trend": interview_svc.metrics(
                    company_ids,
                    today_start=today_start,
                    week_start=week_start,
                    prev_week_start=prev_week_start,
                    interviews_today=interviews_today,
                )["trend"],
                "subtitle": "Scheduled for today"
                if interviews_today
                else "No interviews today",
            },
            candidate_svc.new_applications_card(
                apps,
                today_start=today_start,
                week_start=week_start,
                prev_week_start=prev_week_start,
            ),
            {
                "key": "pending_reviews",
                "label": "Pending Reviews",
                "value": format_stat_value(pending),
                "icon": "pending_actions",
                "tone": "secondary",
                "trend": _trend_for_count(pending_week, pending_prev_week).to_dict(),
                "subtitle": "Awaiting screening" if pending else "All caught up",
            },
            candidate_svc.shortlisted_card(
                apps, week_start=week_start, prev_week_start=prev_week_start
            ),
            offer_svc.metrics(
                apps, week_start=week_start, prev_week_start=prev_week_start
            ),
            {
                "key": "hired_month",
                "label": "Hired This Month",
                "value": format_stat_value(hired_month),
                "icon": "person_add",
                "tone": "tertiary",
                "trend": _trend_for_count(
                    hired_month,
                    apps.filter(
                        status=JobApplicationStatus.HIRED,
                        hired_at__gte=prev_month_start,
                        hired_at__lt=month_start,
                    ).count(),
                    period="last month",
                ).to_dict(),
                "subtitle": f"{hired_month} this month"
                if hired_month
                else "No hires yet this month",
            },
            hiring_svc.metrics(
                apps,
                month_start=month_start,
                week_start=week_start,
                prev_week_start=prev_week_start,
            ),
        ]

    def build_reporting_metrics(self, recruiter: RecruiterProfile) -> dict:
        """Derived rates and timing metrics for analytics reporting."""
        _, today_start, _, _, month_start, _ = self._time_windows()
        company_ids, apps = self._base_querysets(recruiter)

        total = apps.count() or 1
        shortlisted = apps.filter(status=JobApplicationStatus.SHORTLISTED).count()
        interviewed = apps.filter(
            status__in=(
                JobApplicationStatus.INTERVIEW_COMPLETED,
                JobApplicationStatus.OFFER_RELEASED,
                JobApplicationStatus.HIRED,
            )
        ).count()
        interview_scheduled = apps.filter(
            status=JobApplicationStatus.INTERVIEW_SCHEDULED
        ).count()
        interview_total = interviewed + interview_scheduled
        offers = apps.filter(status=JobApplicationStatus.OFFER_RELEASED).count()
        accepted = apps.filter(status=JobApplicationStatus.OFFER_ACCEPTED).count()
        hired = apps.filter(status=JobApplicationStatus.HIRED).count()

        hired_qs = apps.filter(
            status=JobApplicationStatus.HIRED, hired_at__isnull=False
        )
        avg_days = None
        if hired_qs.exists():
            total_days = 0
            n = 0
            for app in hired_qs[:100]:
                if app.hired_at and app.applied_at:
                    total_days += (app.hired_at - app.applied_at).days
                    n += 1
            if n:
                avg_days = round(total_days / n)

        completed_interviews = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
            status=InterviewStatus.COMPLETED,
        ).count()
        all_interviews = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
        ).count()

        return {
            "conversion_rate": round((hired / total) * 100),
            "shortlist_rate": round((shortlisted / total) * 100),
            "interview_completion_rate": round(
                (completed_interviews / all_interviews) * 100
            )
            if all_interviews
            else 0,
            "interview_success_rate": round((interviewed / interview_total) * 100)
            if interview_total
            else 0,
            "offer_acceptance_rate": round((accepted / offers) * 100) if offers else 0,
            "time_to_hire_days": avg_days,
            "hired_this_month": apps.filter(
                status=JobApplicationStatus.HIRED, hired_at__gte=month_start
            ).count(),
        }

    def build_stat_cards(self, recruiter: RecruiterProfile) -> list[dict]:
        """Dashboard KPI row — four primary cards only."""
        return self.build_primary_kpi_cards(recruiter)


def _interviews_today_count(company_ids, today_start) -> int:
    tomorrow = today_start + timedelta(days=1)
    return JobApplicationInterview.objects.filter(
        application__job_posting__company_id__in=company_ids,
        application__is_deleted=False,
        is_deleted=False,
        scheduled_at__gte=today_start,
        scheduled_at__lt=tomorrow,
        status__in=(
            InterviewStatus.SCHEDULED,
            InterviewStatus.CONFIRMED,
            InterviewStatus.IN_PROGRESS,
            InterviewStatus.COMPLETED,
        ),
    ).count()
