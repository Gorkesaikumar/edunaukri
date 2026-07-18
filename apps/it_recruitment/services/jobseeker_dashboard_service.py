"""Aggregate dashboard data for the Job Seeker portal."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.dashboard_recommendation_engine import (
    DashboardRecommendationEngine,
    HeroCardContext,
)
from apps.it_recruitment.services.jobseeker_dashboard_kpi_service import (
    DashboardKPIBundle,
    JobSeekerDashboardKPIService,
)
from apps.it_recruitment.constants.recommendation_constants import (
    DASHBOARD_RECOMMENDATION_LIMIT,
)
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.job_recommendation_engine_service import (
    JobRecommendationEngineService,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    greeting_for_hour,
    media_url,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
    ProfileCompletionDashboardState,
)
from apps.jobs.models import SavedJob
from apps.notifications.models import Notification


STATUS_BADGE_MAP = {
    JobApplicationStatus.APPLIED: ("Applied", "jsd-badge--muted"),
    JobApplicationStatus.UNDER_REVIEW: ("Under Review", "jsd-badge--info"),
    JobApplicationStatus.SHORTLISTED: ("Shortlisted", "jsd-badge--success"),
    JobApplicationStatus.INTERVIEW_SCHEDULED: (
        "Interview Scheduled",
        "jsd-badge--info",
    ),
    JobApplicationStatus.INTERVIEW_COMPLETED: (
        "Interview Completed",
        "jsd-badge--info",
    ),
    JobApplicationStatus.OFFER_RELEASED: ("Offer Released", "jsd-badge--success"),
    JobApplicationStatus.OFFER_ACCEPTED: ("Offer Accepted", "jsd-badge--success"),
    JobApplicationStatus.OFFER_DECLINED: ("Offer Declined", "jsd-badge--muted"),
    JobApplicationStatus.HIRED: ("Hired", "jsd-badge--success"),
    JobApplicationStatus.REJECTED: ("Rejected", "jsd-badge--danger"),
    JobApplicationStatus.WITHDRAWN: ("Withdrawn", "jsd-badge--muted"),
    JobApplicationStatus.EXPIRED: ("Expired", "jsd-badge--muted"),
}


@dataclass
class StatCard:
    key: str
    label: str
    value: str
    icon: str
    icon_tone: str
    trend_label: str
    trend_tone: str
    trend_icon: str
    subtitle: str = ""
    tooltip: str = ""
    pct_badge: str = ""

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "icon": self.icon,
            "icon_tone": self.icon_tone,
            "trend_label": self.trend_label,
            "trend_tone": self.trend_tone,
            "trend_icon": self.trend_icon,
            "subtitle": self.subtitle,
            "tooltip": self.tooltip,
            "pct_badge": self.pct_badge,
        }


@dataclass
class RecommendedJobCard:
    id: str
    title: str
    company_name: str
    logo_url: str | None
    match_percent: int
    tags: list[str]
    salary_display: str
    apply_url: str
    save_url: str
    detail_url: str
    is_saved: bool


@dataclass
class ApplicationRow:
    id: str
    title: str
    company_name: str
    logo_url: str | None
    status_label: str
    status_class: str
    applied_date: str
    track_url: str


@dataclass
class InterviewItem:
    id: str
    title: str
    company_name: str
    schedule_label: str
    is_today: bool
    meet_url: str | None
    detail_url: str


@dataclass
class NotificationItem:
    id: str
    title: str
    body: str
    is_read: bool
    created_at: str
    mark_read_url: str


@dataclass
class DashboardContext:
    greeting: str
    display_name: str
    headline: str
    profile_completion: int
    new_matches_count: int
    match_departments: str
    welcome_message: str
    hero: HeroCardContext | None = None
    completion: ProfileCompletionDashboardState | None = None
    show_completion_card: bool = False
    stats: list[StatCard] = field(default_factory=list)
    recommended_jobs: list[RecommendedJobCard] = field(default_factory=list)
    recent_applications: list[ApplicationRow] = field(default_factory=list)
    upcoming_interviews: list[InterviewItem] = field(default_factory=list)
    notifications: list[NotificationItem] = field(default_factory=list)
    unread_notification_count: int = 0
    skills: list[str] = field(default_factory=list)
    experience_display: str = ""
    notice_period_display: str = ""
    avatar_url: str | None = None
    salary_benchmark: dict = field(default_factory=dict)
    kpis: DashboardKPIBundle | None = None


class JobSeekerDashboardService:
    """Build template-ready dashboard context from live database records."""

    def build(
        self, *, user, profile: JobSeekerProfile | None = None
    ) -> DashboardContext:
        profile = (
            profile
            or JobSeekerProfile.objects.filter(user=user, is_deleted=False)
            .select_related("profile_photo", "resume_file")
            .prefetch_related("skills__skill", "experiences", "education")
            .first()
        )
        if profile is None:
            return self._empty_context(user)

        hero = DashboardRecommendationEngine().build(profile)
        completion = JobSeekerProfileCompletionService().get_dashboard_state(profile)

        now = timezone.localtime()
        greeting = greeting_for_hour(now.hour)
        display_name = profile.full_name or user.email.split("@")[0]

        kpi_service = JobSeekerDashboardKPIService()
        kpis = kpi_service.build(profile)

        applications_qs = JobApplication.objects.filter(
            job_seeker=profile, is_deleted=False
        ).select_related(
            "job_posting", "job_posting__company", "job_posting__company__logo_file"
        )

        stats = self._build_stats(profile, applications_qs, kpis, kpi_service)
        recommended = self._recommended_jobs(profile)
        recent_apps = self._recent_applications(applications_qs, user)
        interviews = self._upcoming_interviews(applications_qs, user)
        notifications, unread = self._notifications(user)
        skills = [js.skill.name for js in profile.skills.all()[:6] if js.skill_id]
        match_departments = ", ".join(skills[:2]) if skills else "your preferred roles"

        snapshot = JobRecommendationCacheService().get_snapshot(profile)
        new_matches = (
            snapshot.new_matches_count
            if snapshot
            else (hero.matching_jobs_count if hero else 0)
        )

        return DashboardContext(
            greeting=greeting,
            display_name=display_name,
            headline=profile.headline or "Job Seeker",
            profile_completion=completion.percentage,
            new_matches_count=new_matches,
            match_departments=match_departments,
            welcome_message=hero.message if hero else "Welcome back to your dashboard.",
            hero=hero,
            completion=completion,
            show_completion_card=completion.show_completion_card,
            stats=stats,
            recommended_jobs=recommended,
            recent_applications=recent_apps,
            upcoming_interviews=interviews,
            notifications=notifications,
            unread_notification_count=unread,
            skills=skills,
            experience_display=self._format_experience(profile.experience_years),
            notice_period_display=self._format_notice_period(
                profile.notice_period_days
            ),
            avatar_url=media_url(profile.profile_photo),
            salary_benchmark=self._salary_benchmark(profile),
            kpis=kpis,
        )

    def _empty_context(self, user) -> DashboardContext:
        now = timezone.localtime()
        return DashboardContext(
            greeting=greeting_for_hour(now.hour),
            display_name=user.email.split("@")[0],
            headline="Job Seeker",
            profile_completion=0,
            new_matches_count=0,
            match_departments="your preferred roles",
            welcome_message="Complete your profile to unlock personalized job recommendations.",
            salary_benchmark={"current_pct": 40, "average_pct": 65, "top_pct": 90},
        )

    def _build_stats(
        self,
        profile: JobSeekerProfile,
        applications_qs,
        kpis: DashboardKPIBundle,
        kpi_service: JobSeekerDashboardKPIService,
    ) -> list[StatCard]:
        saved_qs = SavedJob.objects.filter(job_seeker=profile, is_deleted=False)
        views_qs = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
        )
        interview_qs = applications_qs.filter(
            status__in=[
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplicationStatus.INTERVIEW_COMPLETED,
            ]
        )

        apps_trend = kpi_service.trend_for_queryset(applications_qs, "applied_at")
        saved_trend = kpi_service.weekly_trend(saved_qs, "created_at")
        interview_trend = kpi_service.trend_for_queryset(
            applications_qs.filter(status=JobApplicationStatus.INTERVIEW_SCHEDULED),
            "status_changed_at",
            period_days=30,
            count_label="this month",
        )
        views_trend = kpi_service.weekly_trend(views_qs, "created_at")

        apps_subtitle = (
            f"{kpis.applications_under_review} under review"
            if kpis.applications_under_review
            else "No active applications"
        )
        if kpis.applications_total and kpis.application_success_rate:
            apps_subtitle += f" · {kpis.application_success_rate}% success rate"

        saved_subtitle = (
            f"{kpis.matching_jobs_total} jobs match your profile"
            if kpis.matching_jobs_total
            else "Save roles to track opportunities"
        )
        if kpis.new_matches_count:
            saved_subtitle = f"{kpis.new_matches_count} new matches · {saved_subtitle}"

        interview_count = interview_qs.count()
        interview_subtitle = (
            f"{kpis.interview_pending} awaiting your response"
            if kpis.interview_pending
            else "No pending invitations"
        )

        views_subtitle = (
            f"{kpis.profile_views_today} viewed today"
            if kpis.profile_views_today
            else "Share your profile to get noticed"
        )

        return [
            StatCard(
                key="applications",
                label="Applications",
                value=str(kpis.applications_total),
                icon="bi-send",
                icon_tone="primary",
                trend_label=apps_trend.label,
                trend_tone=apps_trend.tone,
                trend_icon=apps_trend.icon,
                subtitle=apps_subtitle,
                tooltip="Total job applications and monthly activity trend",
                pct_badge=f"{kpis.application_success_rate}% success"
                if kpis.applications_total
                else "",
            ),
            StatCard(
                key="saved_jobs",
                label="Saved Jobs",
                value=str(kpis.saved_jobs_total),
                icon="bi-bookmark",
                icon_tone="secondary",
                trend_label=saved_trend.label,
                trend_tone=saved_trend.tone,
                trend_icon=saved_trend.icon,
                subtitle=saved_subtitle,
                tooltip="Jobs you saved and matching opportunities from your preferences",
                pct_badge=f"{kpis.resume_match_score}% match"
                if kpis.resume_match_score
                else "",
            ),
            StatCard(
                key="interviews",
                label="Interview Invites",
                value=f"{interview_count:02d}"
                if interview_count < 10
                else str(interview_count),
                icon="bi-calendar-check",
                icon_tone="tertiary",
                trend_label=interview_trend.label,
                trend_tone=interview_trend.tone,
                trend_icon=interview_trend.icon,
                subtitle=interview_subtitle,
                tooltip="Scheduled and completed interview invitations",
                pct_badge=f"{kpis.recruiter_interest_score}% interest"
                if kpis.recruiter_interest_score
                else "",
            ),
            StatCard(
                key="profile_views",
                label="Profile Views",
                value=self._format_profile_views(kpis.profile_views_total),
                icon="bi-eye",
                icon_tone="primary-dim",
                trend_label=views_trend.label,
                trend_tone=views_trend.tone,
                trend_icon=views_trend.icon,
                subtitle=views_subtitle,
                tooltip="Recruiter profile views and weekly visibility trend",
                pct_badge=(
                    f"+{kpis.profile_visibility_change}% weekly"
                    if kpis.profile_visibility_change > 0
                    else ""
                ),
            ),
        ]

    @staticmethod
    def _format_profile_views(count) -> str:
        count = int(count or 0)
        if count >= 1000:
            return f"{count / 1000:.1f}k".replace(".0k", "k")
        return str(count)

    @staticmethod
    def _format_experience(years) -> str:
        if years is None:
            return "—"
        if years == 1:
            return "1 Year"
        return f"{years} Years"

    @staticmethod
    def _format_notice_period(days) -> str:
        if days is None:
            return "—"
        if days == 1:
            return "1 Day"
        return f"{days} Days"

    def _recommended_jobs(self, profile) -> list[RecommendedJobCard]:
        from django.urls import reverse

        pu = lambda name, **kw: PortalURLService.jobseeker(profile.user, name, **kw)
        cache = JobRecommendationCacheService()
        rows = list(
            cache.get_cached_rows(profile, limit=DASHBOARD_RECOMMENDATION_LIMIT)
        )
        if not rows:
            JobRecommendationEngineService().get_recommendations(
                profile,
                limit=DASHBOARD_RECOMMENDATION_LIMIT,
                force_rebuild=True,
            )
            rows = list(
                cache.get_cached_rows(profile, limit=DASHBOARD_RECOMMENDATION_LIMIT)
            )

        saved_ids = set(
            SavedJob.objects.filter(job_seeker=profile, is_deleted=False).values_list(
                "job_posting_id", flat=True
            )
        )

        cards: list[RecommendedJobCard] = []
        for row in rows:
            job = row.job_posting
            tags = []
            if job.employment_type:
                tags.append(job.get_employment_type_display())
            if job.work_mode:
                tags.append(job.get_work_mode_display())
            if job.category:
                tags.append(job.category)

            cards.append(
                RecommendedJobCard(
                    id=str(job.pk),
                    title=job.title,
                    company_name=job.company_name_snapshot or job.company.name,
                    logo_url=media_url(job.company.logo_file)
                    if job.company_id
                    else None,
                    match_percent=row.match_score,
                    tags=tags[:2],
                    salary_display=format_salary_lpa(
                        job.salary_min, job.salary_max, job.salary_currency
                    ),
                    apply_url=pu("jobseeker_job_apply", job_id=job.pk),
                    save_url=pu("jobseeker_save_job", job_id=job.pk),
                    detail_url=reverse(
                        "marketplace_job_detail", kwargs={"job_id": job.pk}
                    ),
                    is_saved=job.pk in saved_ids,
                )
            )
        return cards

    def _recent_applications(self, applications_qs, user) -> list[ApplicationRow]:
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        rows: list[ApplicationRow] = []
        for app in applications_qs.order_by("-applied_at")[:5]:
            status_label, status_class = STATUS_BADGE_MAP.get(
                app.status, (app.get_status_display(), "jsd-badge--muted")
            )
            logo = None
            if app.job_posting_id and app.job_posting.company_id:
                logo = media_url(app.job_posting.company.logo_file)
            rows.append(
                ApplicationRow(
                    id=str(app.pk),
                    title=app.job_title_snapshot
                    or (app.job_posting.title if app.job_posting_id else ""),
                    company_name=app.company_name_snapshot or "",
                    logo_url=logo,
                    status_label=status_label,
                    status_class=status_class,
                    applied_date=timezone.localtime(app.applied_at).strftime(
                        "%b %d, %Y"
                    ),
                    track_url=pu("jobseeker_application_detail", application_id=app.pk),
                )
            )
        return rows

    def _upcoming_interviews(self, applications_qs, user) -> list[InterviewItem]:
        from django.urls import reverse

        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        now = timezone.localtime()
        items: list[InterviewItem] = []
        interview_apps = applications_qs.filter(
            status__in=[
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplicationStatus.INTERVIEW_COMPLETED,
            ]
        ).order_by("status_changed_at")[:5]

        for app in interview_apps:
            scheduled = timezone.localtime(app.status_changed_at)
            is_today = scheduled.date() == now.date()
            if is_today:
                schedule_label = f"Today • {scheduled.strftime('%I:%M %p').lstrip('0')}"
            else:
                schedule_label = scheduled.strftime("%b %d • %I:%M %p").replace(
                    " 0", " "
                )

            meet_url = None
            event = (
                app.timeline.filter(event_type="status_changed")
                .order_by("-occurred_at")
                .first()
            )
            if event and event.metadata:
                meet_url = event.metadata.get("meet_url") or event.metadata.get(
                    "meeting_url"
                )

            items.append(
                InterviewItem(
                    id=str(app.pk),
                    title=app.job_title_snapshot or "Interview",
                    company_name=app.company_name_snapshot or "",
                    schedule_label=schedule_label,
                    is_today=is_today,
                    meet_url=meet_url,
                    detail_url=pu(
                        "jobseeker_application_detail", application_id=app.pk
                    ),
                )
            )
        return items

    def _notifications(self, user) -> tuple[list[NotificationItem], int]:
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)

        qs = Notification.objects.filter(
            recipient_domain="it", recipient_id=user.pk
        ).order_by("-created_at")[:8]
        unread = Notification.objects.filter(
            recipient_domain="it", recipient_id=user.pk, is_read=False
        ).count()
        items = [
            NotificationItem(
                id=str(n.pk),
                title=n.title,
                body=n.body,
                is_read=n.is_read,
                created_at=timezone.localtime(n.created_at).strftime("%b %d, %I:%M %p"),
                mark_read_url=pu("jobseeker_notification_read", notification_id=n.pk),
            )
            for n in qs
        ]
        return items, unread

    @staticmethod
    def _salary_benchmark(profile) -> dict:
        current = float(profile.current_salary or 0)
        expected = float(profile.expected_salary or 0)
        if current <= 0 and expected <= 0:
            return {
                "current_pct": 40,
                "average_pct": 65,
                "top_pct": 90,
                "has_data": False,
            }
        benchmark = max(current, expected, 1)
        avg = benchmark * 1.35
        top = benchmark * 1.85
        scale = top or 1
        return {
            "has_data": True,
            "current_pct": max(15, int((current / scale) * 100)) if current else 35,
            "average_pct": int((avg / scale) * 100),
            "top_pct": 90,
        }
