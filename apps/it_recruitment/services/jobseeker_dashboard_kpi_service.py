"""Live KPI calculations for the Job Seeker dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerJobRecommendation, JobSeekerProfile
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.jobs.models import SavedJob
from apps.notifications.models import Notification


LIVE_ACTIVITY_EVENT_TYPES = (
    "job.recommended",
    "application.status_changed",
    "application.submitted",
    "profile_viewed",
)


@dataclass
class TrendIndicator:
    label: str
    tone: str = "muted"
    icon: str = "bi-dash"

    def to_dict(self) -> dict:
        return {"label": self.label, "tone": self.tone, "icon": self.icon}


@dataclass
class DashboardKPIBundle:
    profile_completion: int
    resume_match_score: int
    recruiter_interest_score: int
    application_success_rate: int
    profile_visibility_change: int
    matching_jobs_total: int
    new_matches_count: int
    applications_total: int
    applications_under_review: int
    applications_shortlisted: int
    interview_pending: int
    profile_views_total: int
    profile_views_today: int
    saved_jobs_total: int
    activity_insights: list[str] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "profile_completion": self.profile_completion,
            "resume_match_score": self.resume_match_score,
            "recruiter_interest_score": self.recruiter_interest_score,
            "application_success_rate": self.application_success_rate,
            "profile_visibility_change": self.profile_visibility_change,
            "matching_jobs_total": self.matching_jobs_total,
            "new_matches_count": self.new_matches_count,
            "applications_total": self.applications_total,
            "applications_under_review": self.applications_under_review,
            "applications_shortlisted": self.applications_shortlisted,
            "interview_pending": self.interview_pending,
            "profile_views_total": self.profile_views_total,
            "profile_views_today": self.profile_views_today,
            "saved_jobs_total": self.saved_jobs_total,
            "activity_insights": self.activity_insights,
            "updated_at": self.updated_at,
        }


class JobSeekerDashboardKPIService(BaseService):
    """Compute real-time dashboard metrics from database activity."""

    UNDER_REVIEW_STATUSES = (
        JobApplicationStatus.APPLIED,
        JobApplicationStatus.UNDER_REVIEW,
    )
    SUCCESS_STATUSES = (
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    )

    def build(self, profile: JobSeekerProfile) -> DashboardKPIBundle:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        completion = JobSeekerProfileCompletionService().get_dashboard_state(profile)
        applications = JobApplication.objects.filter(
            job_seeker=profile, is_deleted=False
        )
        saved_jobs = SavedJob.objects.filter(job_seeker=profile, is_deleted=False)
        views_qs = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
        )

        apps_total = applications.count()
        under_review = applications.filter(
            status__in=self.UNDER_REVIEW_STATUSES
        ).count()
        shortlisted = applications.filter(
            status=JobApplicationStatus.SHORTLISTED
        ).count()
        interview_pending = applications.filter(
            status=JobApplicationStatus.INTERVIEW_SCHEDULED
        ).count()
        success_count = applications.filter(status__in=self.SUCCESS_STATUSES).count()
        success_rate = round((success_count / apps_total) * 100) if apps_total else 0

        saved_total = saved_jobs.count()
        views_total = views_qs.count()
        views_today = views_qs.filter(created_at__gte=today_start).count()
        views_this_week = views_qs.filter(created_at__gte=week_start).count()
        views_prev_week = views_qs.filter(
            created_at__gte=prev_week_start, created_at__lt=week_start
        ).count()
        visibility_change = self._percent_change(views_this_week, views_prev_week)

        snapshot = JobRecommendationCacheService().get_snapshot(profile)
        matching_total = snapshot.total_matches if snapshot else 0
        new_matches = snapshot.new_matches_count if snapshot else 0
        top_match = snapshot.top_match_score if snapshot else 0
        resume_match = top_match or self._fallback_match_score(
            profile, completion.percentage
        )

        recruiter_interest = min(
            100,
            int(
                min(views_this_week * 10, 40)
                + min(shortlisted * 8, 24)
                + min(interview_pending * 12, 24)
                + completion.percentage * 0.12
            ),
        )

        insights = self._collect_live_activity_updates(
            profile=profile,
            snapshot=snapshot,
            matching_total=matching_total,
            new_matches=new_matches,
        )

        return DashboardKPIBundle(
            profile_completion=completion.percentage,
            resume_match_score=resume_match,
            recruiter_interest_score=recruiter_interest,
            application_success_rate=success_rate,
            profile_visibility_change=visibility_change,
            matching_jobs_total=matching_total,
            new_matches_count=new_matches,
            applications_total=apps_total,
            applications_under_review=under_review,
            applications_shortlisted=shortlisted,
            interview_pending=interview_pending,
            profile_views_total=views_total,
            profile_views_today=views_today,
            saved_jobs_total=saved_total,
            activity_insights=insights,
            updated_at=timezone.localtime(now).strftime("%b %d, %I:%M %p"),
        )

    def trend_for_queryset(
        self,
        qs: QuerySet,
        date_field: str,
        *,
        period_days: int = 30,
        count_label: str = "this month",
    ) -> TrendIndicator:
        now = timezone.now()
        current_start = now - timedelta(days=period_days)
        previous_start = now - timedelta(days=period_days * 2)
        current = qs.filter(**{f"{date_field}__gte": current_start}).count()
        previous = qs.filter(
            **{f"{date_field}__gte": previous_start, f"{date_field}__lt": current_start}
        ).count()
        return self._trend_from_counts(current, previous, count_label=count_label)

    def weekly_trend(self, qs: QuerySet, date_field: str) -> TrendIndicator:
        return self.trend_for_queryset(
            qs, date_field, period_days=7, count_label="this week"
        )

    @staticmethod
    def _percent_change(current: int, previous: int) -> int:
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100)

    @staticmethod
    def _trend_from_counts(
        current: int, previous: int, *, count_label: str
    ) -> TrendIndicator:
        if previous == 0:
            if current > 0:
                return TrendIndicator(
                    label=f"+{current} {count_label}",
                    tone="success",
                    icon="bi-graph-up-arrow",
                )
            return TrendIndicator(
                label=f"0 {count_label}", tone="muted", icon="bi-dash"
            )
        change = round(((current - previous) / previous) * 100)
        if change > 0:
            return TrendIndicator(
                label=f"+{change}%",
                tone="success",
                icon="bi-graph-up-arrow",
            )
        if change < 0:
            return TrendIndicator(
                label=f"{change}%",
                tone="danger",
                icon="bi-graph-down-arrow",
            )
        return TrendIndicator(label="No change", tone="muted", icon="bi-dash")

    @staticmethod
    def _fallback_match_score(profile: JobSeekerProfile, completion_pct: int) -> int:
        base = max(40, min(85, completion_pct))
        if profile.resume_file_id:
            base += 5
        if profile.skills.filter(is_deleted=False).exists():
            base += 5
        return min(99, base)

    def _collect_live_activity_updates(
        self,
        *,
        profile: JobSeekerProfile,
        snapshot,
        matching_total: int,
        new_matches: int,
        limit: int = 8,
    ) -> list[str]:
        """Build ticker messages from notifications, applications, and recommendation cache."""
        now = timezone.now()
        cutoff = now - timedelta(days=14)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        updates: list[tuple] = []
        seen: set[str] = set()

        def add(when, text: str) -> None:
            cleaned = " ".join((text or "").split())
            if not cleaned or cleaned in seen:
                return
            seen.add(cleaned)
            updates.append((when, cleaned))

        for notif in Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            created_at__gte=cutoff,
            event_type__in=LIVE_ACTIVITY_EVENT_TYPES,
        ).order_by("-created_at")[: limit * 2]:
            add(notif.created_at, notif.body or notif.title)

        cache = JobRecommendationCacheService()
        for rec in (
            JobSeekerJobRecommendation.objects.filter(
                job_seeker=profile,
                is_deleted=False,
                is_new=True,
            )
            .select_related("job_posting")
            .order_by("-computed_at", "-match_score")[:5]
        ):
            job = rec.job_posting
            company = job.company_name_snapshot or "a hiring company"
            add(
                rec.computed_at,
                f"New match: {job.title} at {company} — {rec.match_score}% fit with your profile.",
            )

        if snapshot and snapshot.computed_at and snapshot.computed_at >= cutoff:
            if snapshot.top_match_job_id and snapshot.top_match_job:
                job = snapshot.top_match_job
                company = job.company_name_snapshot or "a hiring company"
                add(
                    snapshot.computed_at,
                    f"Top match: {job.title} at {company} ({snapshot.top_match_score}% match).",
                )
            elif new_matches > 0:
                add(
                    snapshot.computed_at,
                    f"{new_matches} new job{'s' if new_matches != 1 else ''} added to your matches.",
                )
            elif matching_total > 0:
                add(
                    snapshot.computed_at,
                    f"{matching_total} open roles match your career preferences right now.",
                )

        views_today = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
            created_at__gte=today_start,
        ).count()
        if views_today > 0:
            add(
                now,
                f"{views_today} recruiter{'s' if views_today != 1 else ''} viewed your profile today.",
            )

        updates.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in updates[:limit]]
