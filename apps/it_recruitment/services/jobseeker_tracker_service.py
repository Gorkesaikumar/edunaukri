"""Job seeker career tracker — command center aggregating applications, activity, and analytics."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService

from apps.applications.constants.enums import (
    JobApplicationStatus,
    TERMINAL_STATUSES,
    TimelineEventType,
)
from apps.applications.models import JobApplication, JobApplicationTimelineEvent
from apps.applications.selectors.application_selector import JobApplicationSelector
from apps.applications.selectors.timeline_selector import JobApplicationTimelineSelector
from apps.applications.services.application_statistics_service import (
    ApplicationStatisticsService,
)
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerJobRecommendation, JobSeekerProfile
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.jobseeker_application_portal_service import (
    JobSeekerApplicationPortalService,
    STATUS_UI,
)
from apps.it_recruitment.services.jobseeker_dashboard_kpi_service import (
    JobSeekerDashboardKPIService,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import media_url
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.jobs.models import SavedJob
from apps.notifications.models import Notification


STATUS_RANK = {
    JobApplicationStatus.APPLIED: 1,
    JobApplicationStatus.UNDER_REVIEW: 2,
    JobApplicationStatus.SHORTLISTED: 3,
    JobApplicationStatus.INTERVIEW_SCHEDULED: 4,
    JobApplicationStatus.INTERVIEW_COMPLETED: 5,
    JobApplicationStatus.OFFER_RELEASED: 6,
    JobApplicationStatus.OFFER_ACCEPTED: 7,
    JobApplicationStatus.HIRED: 8,
    JobApplicationStatus.REJECTED: 0,
    JobApplicationStatus.WITHDRAWN: 0,
    JobApplicationStatus.EXPIRED: 0,
    JobApplicationStatus.OFFER_DECLINED: 0,
}

PIPELINE_STAGE_DEFS = (
    ("applied", "Applied", 1),
    ("resume_viewed", "Resume Viewed", 2),
    ("profile_reviewed", "Profile Reviewed", 2),
    ("shortlisted", "Shortlisted", 3),
    ("assessment", "Assessment", 3),
    ("interview", "Interview", 4),
    ("hr_discussion", "HR Discussion", 5),
    ("offer", "Offer Released", 6),
    ("joined", "Joined", 8),
)


@dataclass
class TrackerSummaryCard:
    key: str
    label: str
    value: str
    raw_value: int
    icon: str
    tone: str


@dataclass
class PipelineStage:
    key: str
    label: str
    state: str  # completed | current | pending | skipped
    timestamp: str
    recruiter_name: str
    description: str


@dataclass
class ApplicationPipeline:
    application_id: str
    job_title: str
    company_name: str
    logo_url: str | None
    status: str
    status_label: str
    detail_url: str
    stages: list[PipelineStage]
    current_index: int


@dataclass
class ActivityFeedItem:
    id: str
    icon: str
    tone: str
    title: str
    subtitle: str
    company: str
    job_title: str
    status_label: str
    recruiter_name: str
    occurred_date: str
    occurred_time: str
    detail_url: str | None
    source: str


@dataclass
class ChartBar:
    label: str
    value: int
    pct: float


@dataclass
class ProfileInsight:
    key: str
    message: str
    action_label: str
    action_url: str
    tone: str


@dataclass
class InterviewTrackerItem:
    application_id: str
    job_title: str
    company_name: str
    state: str  # upcoming | completed | cancelled
    interview_type: str
    date_label: str
    time_label: str
    meet_url: str | None
    panel: str
    instructions: str
    countdown_label: str | None
    detail_url: str


@dataclass
class OfferTrackerItem:
    application_id: str
    job_title: str
    company_name: str
    state: str  # pending | accepted | declined
    salary_display: str
    joining_date: str
    expiry_label: str | None
    letter_url: str | None
    detail_url: str


@dataclass
class MatchJobItem:
    id: str
    title: str
    company_name: str
    match_percent: int
    detail_url: str
    is_new: bool


@dataclass
class TrackerPageContext:
    summary: list[TrackerSummaryCard]
    pipelines: list[ApplicationPipeline]
    activities: list[ActivityFeedItem]
    profile_analytics: dict
    application_charts: dict
    interviews: list[InterviewTrackerItem]
    offers: list[OfferTrackerItem]
    profile_insights: list[ProfileInsight]
    match_jobs: list[MatchJobItem]
    match_score: int
    updated_at: str
    filters: dict


class JobSeekerTrackerService(BaseService):
    """Aggregate tracker dashboard data for the authenticated job seeker."""

    def __init__(self):
        self._apps = JobApplicationSelector()
        self._timeline = JobApplicationTimelineSelector()
        self._portal = JobSeekerApplicationPortalService()
        self._kpis = JobSeekerDashboardKPIService()
        self._stats = ApplicationStatisticsService()

    def build(
        self,
        profile: JobSeekerProfile,
        *,
        q: str = "",
        status: str = "",
        company: str = "",
        activity_page: int = 1,
        activity_page_size: int = 20,
    ) -> TrackerPageContext:
        kpis = self._kpis.build(profile)
        stats = self._stats.seeker_dashboard(profile)
        by_status = stats.get("applications_by_status", {})
        active = stats.get("active_applications", 0)

        applications = self._applications_qs(
            profile, q=q, status=status, company=company
        )
        user = profile.user
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        pipelines = [self._build_pipeline(app, pu) for app in applications[:12]]
        activities = self._build_activity_feed(profile, applications, pu, q=q)
        paginated_activities = self._paginate_activities(
            activities, activity_page, activity_page_size
        )

        return TrackerPageContext(
            summary=self._summary_cards(kpis, by_status, active),
            pipelines=pipelines,
            activities=paginated_activities,
            profile_analytics=self._profile_analytics(kpis, profile),
            application_charts=self._application_charts(profile, by_status),
            interviews=self._interview_tracker(applications, pu),
            offers=self._offer_tracker(applications, pu),
            profile_insights=self._profile_insights(profile, pu),
            match_jobs=self._match_jobs(profile),
            match_score=kpis.resume_match_score,
            updated_at=kpis.updated_at,
            filters={
                "q": q,
                "status": status,
                "company": company,
                "activity_page": activity_page,
            },
        )

    def export_csv(self, profile: JobSeekerProfile) -> str:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        activities = self._build_activity_feed(
            profile, self._applications_qs(profile), pu
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["Date", "Time", "Title", "Company", "Job", "Status", "Recruiter", "Source"]
        )
        for item in activities:
            writer.writerow(
                [
                    item.occurred_date,
                    item.occurred_time,
                    item.title,
                    item.company,
                    item.job_title,
                    item.status_label,
                    item.recruiter_name,
                    item.source,
                ]
            )
        return buffer.getvalue()

    def _applications_qs(self, profile, *, q="", status="", company=""):
        qs = (
            self._apps.for_seeker(profile)
            .select_related(
                "job_posting",
                "job_posting__company",
                "job_posting__company__logo_file",
                "job_posting__posted_by",
            )
            .prefetch_related("timeline")
        )
        if status:
            qs = qs.filter(status=status)
        if company:
            qs = qs.filter(company_name_snapshot__icontains=company)
        if q:
            qs = qs.filter(
                Q(job_title_snapshot__icontains=q)
                | Q(company_name_snapshot__icontains=q)
            )
        return qs.order_by("-applied_at")

    def _summary_cards(
        self, kpis, by_status: dict, active: int
    ) -> list[TrackerSummaryCard]:
        cards = [
            (
                "applications",
                "Total Applications",
                kpis.applications_total,
                "bi-briefcase-fill",
                "primary",
            ),
            (
                "active",
                "Active Applications",
                active,
                "bi-lightning-charge-fill",
                "info",
            ),
            (
                "review",
                "Under Review",
                kpis.applications_under_review,
                "bi-eye-fill",
                "review",
            ),
            (
                "profile_views",
                "Recruiter Profile Views",
                kpis.profile_views_total,
                "bi-person-lines-fill",
                "info",
            ),
            (
                "resume_views",
                "Resume Views",
                by_status.get(JobApplicationStatus.UNDER_REVIEW, 0),
                "bi-file-earmark-person",
                "review",
            ),
            (
                "shortlisted",
                "Shortlisted",
                kpis.applications_shortlisted,
                "bi-star-fill",
                "success",
            ),
            (
                "interviews",
                "Interviews Scheduled",
                kpis.interview_pending,
                "bi-calendar-event-fill",
                "interview",
            ),
            (
                "assessments",
                "Assessments Pending",
                by_status.get(JobApplicationStatus.UNDER_REVIEW, 0),
                "bi-clipboard-check",
                "review",
            ),
            (
                "offers",
                "Offers Received",
                by_status.get(JobApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(JobApplicationStatus.OFFER_ACCEPTED, 0),
                "bi-envelope-open-heart-fill",
                "offer",
            ),
            (
                "hired",
                "Hired",
                by_status.get(JobApplicationStatus.HIRED, 0),
                "bi-trophy-fill",
                "hired",
            ),
            (
                "rejected",
                "Rejected",
                by_status.get(JobApplicationStatus.REJECTED, 0),
                "bi-x-circle-fill",
                "danger",
            ),
            (
                "saved",
                "Saved Jobs",
                kpis.saved_jobs_total,
                "bi-bookmark-fill",
                "primary",
            ),
            (
                "completion",
                "Profile Completion",
                kpis.profile_completion,
                "bi-person-check-fill",
                "success",
            ),
            (
                "match",
                "Resume Match Score",
                kpis.resume_match_score,
                "bi-bullseye",
                "interview",
            ),
        ]
        return [
            TrackerSummaryCard(
                key=key,
                label=label,
                value=f"{value}%" if key in {"completion", "match"} else str(value),
                raw_value=value,
                icon=icon,
                tone=tone,
            )
            for key, label, value, icon, tone in cards
        ]

    def _build_pipeline(self, app: JobApplication, pu) -> ApplicationPipeline:
        rank = STATUS_RANK.get(app.status, 0)
        if app.status in (
            JobApplicationStatus.REJECTED,
            JobApplicationStatus.WITHDRAWN,
            JobApplicationStatus.EXPIRED,
        ):
            rank = STATUS_RANK.get(app.status, 0)

        events = {e.to_status: e for e in app.timeline.all() if e.to_status}
        recruiter = app.job_posting.posted_by if app.job_posting_id else None
        recruiter_name = recruiter.full_name if recruiter else "Recruiting Team"

        stages: list[PipelineStage] = []
        current_index = 0
        seen_labels: set[str] = set()

        for idx, (key, label, min_rank) in enumerate(PIPELINE_STAGE_DEFS):
            if label in seen_labels:
                continue
            seen_labels.add(label)

            if app.status in TERMINAL_STATUSES and app.status not in (
                JobApplicationStatus.HIRED,
                JobApplicationStatus.OFFER_ACCEPTED,
            ):
                if min_rank > rank and rank > 0:
                    state = "skipped"
                elif min_rank <= rank:
                    state = "completed"
                else:
                    state = "pending"
            elif rank >= min_rank:
                state = "completed"
                current_index = idx
            elif rank + 1 == min_rank or (rank == 0 and min_rank == 1):
                state = "current"
                current_index = idx
            else:
                state = "pending"

            event = self._stage_event(events, min_rank)
            ts = ""
            desc = ""
            actor = recruiter_name
            if event:
                when = timezone.localtime(event.occurred_at)
                ts = when.strftime("%b %d, %Y · %I:%M %p")
                desc = event.notes or STATUS_UI.get(event.to_status or "", {}).get(
                    "description", ""
                )

            if key == "applied" and not event:
                when = timezone.localtime(app.applied_at)
                ts = when.strftime("%b %d, %Y · %I:%M %p")
                desc = "Application submitted successfully."

            stages.append(
                PipelineStage(
                    key=key,
                    label=label,
                    state="current"
                    if idx == current_index and state != "completed"
                    else state,
                    timestamp=ts,
                    recruiter_name=actor,
                    description=desc,
                )
            )

        ui = STATUS_UI.get(app.status, STATUS_UI[JobApplicationStatus.APPLIED])
        logo = None
        if app.job_posting_id and app.job_posting.company_id:
            logo = media_url(app.job_posting.company.logo_file)

        return ApplicationPipeline(
            application_id=str(app.pk),
            job_title=app.job_title_snapshot,
            company_name=app.company_name_snapshot,
            logo_url=logo,
            status=app.status,
            status_label=ui["label"],
            detail_url=pu("jobseeker_application_detail", application_id=app.pk),
            stages=stages,
            current_index=current_index,
        )

    @staticmethod
    def _stage_event(events: dict, min_rank: int):
        for status, event in events.items():
            if STATUS_RANK.get(status, 0) >= min_rank:
                return event
        return None

    def _build_activity_feed(
        self, profile, applications, pu, q=""
    ) -> list[ActivityFeedItem]:
        items: list[ActivityFeedItem] = []
        cutoff = timezone.now() - timedelta(days=90)

        for notif in Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            created_at__gte=cutoff,
        ).order_by("-created_at")[:40]:
            when = timezone.localtime(notif.created_at)
            items.append(
                ActivityFeedItem(
                    id=f"n-{notif.pk}",
                    icon=self._notif_icon(notif.event_type),
                    tone=self._notif_tone(notif.event_type),
                    title=notif.title or "Update",
                    subtitle=notif.body or "",
                    company=self._payload_str(notif.payload, "company_name"),
                    job_title=self._payload_str(notif.payload, "job_title"),
                    status_label=notif.event_type.replace(".", " ")
                    .replace("_", " ")
                    .title(),
                    recruiter_name=self._payload_str(
                        notif.payload, "recruiter_name", "Recruiting Team"
                    ),
                    occurred_date=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                    detail_url=self._payload_url(notif.payload, pu),
                    source="notification",
                )
            )

        app_ids = list(applications.values_list("pk", flat=True)[:50])
        for event in (
            JobApplicationTimelineEvent.objects.filter(
                application_id__in=app_ids, occurred_at__gte=cutoff
            )
            .select_related(
                "application",
                "application__job_posting",
                "application__job_posting__posted_by",
            )
            .order_by("-occurred_at")[:60]
        ):
            app = event.application
            recruiter = app.job_posting.posted_by if app.job_posting_id else None
            when = timezone.localtime(event.occurred_at)
            ui = self._portal._timeline_ui(event)
            items.append(
                ActivityFeedItem(
                    id=f"t-{event.pk}",
                    icon=ui["icon"],
                    tone=ui["tone"],
                    title=ui["title"],
                    subtitle=event.notes or ui["description"],
                    company=app.company_name_snapshot,
                    job_title=app.job_title_snapshot,
                    status_label=app.get_status_display(),
                    recruiter_name=recruiter.full_name
                    if recruiter
                    else "Recruiting Team",
                    occurred_date=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                    detail_url=pu(
                        "jobseeker_application_detail", application_id=app.pk
                    ),
                    source="timeline",
                )
            )

        items.sort(key=lambda x: (x.occurred_date, x.occurred_time), reverse=True)
        if q:
            q_lower = q.lower()
            items = [
                i
                for i in items
                if q_lower in i.title.lower()
                or q_lower in i.subtitle.lower()
                or q_lower in i.company.lower()
                or q_lower in i.job_title.lower()
            ]
        return items

    @staticmethod
    def _paginate_activities(
        items: list[ActivityFeedItem], page: int, page_size: int
    ) -> list[ActivityFeedItem]:
        start = (max(1, page) - 1) * page_size
        return items[start : start + page_size]

    def _profile_analytics(self, kpis, profile: JobSeekerProfile) -> dict:
        skill_count = profile.skills.filter(is_deleted=False).count()
        missing = max(0, 5 - skill_count)
        return {
            "profile_views": kpis.profile_views_total,
            "profile_views_today": kpis.profile_views_today,
            "visibility_change": kpis.profile_visibility_change,
            "recruiter_interest": kpis.recruiter_interest_score,
            "matching_jobs": kpis.matching_jobs_total,
            "new_matches": kpis.new_matches_count,
            "skills_matched": skill_count,
            "missing_skills": missing,
            "avg_match_score": kpis.resume_match_score,
            "success_rate": kpis.application_success_rate,
        }

    def _application_charts(self, profile: JobSeekerProfile, by_status: dict) -> dict:
        apps = JobApplication.objects.filter(job_seeker=profile, is_deleted=False)
        total = apps.count() or 1

        status_bars = [
            ChartBar(
                label=STATUS_UI.get(s, {}).get("label", s.replace("_", " ").title()),
                value=c,
                pct=round((c / total) * 100, 1),
            )
            for s, c in by_status.items()
            if c > 0
        ]

        monthly = (
            apps.annotate(month=TruncMonth("applied_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        month_bars = [
            ChartBar(
                label=timezone.localtime(row["month"]).strftime("%b %Y")
                if row["month"]
                else "—",
                value=row["count"],
                pct=round((row["count"] / total) * 100, 1),
            )
            for row in monthly
        ]

        company_rows = (
            apps.values("company_name_snapshot")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )
        company_bars = [
            ChartBar(
                label=row["company_name_snapshot"] or "Unknown",
                value=row["count"],
                pct=round((row["count"] / total) * 100, 1),
            )
            for row in company_rows
        ]

        interviews = apps.filter(
            status__in=[
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplicationStatus.INTERVIEW_COMPLETED,
            ]
        ).count()
        offers = apps.filter(
            status__in=[
                JobApplicationStatus.OFFER_RELEASED,
                JobApplicationStatus.OFFER_ACCEPTED,
            ]
        ).count()
        shortlisted = apps.filter(status=JobApplicationStatus.SHORTLISTED).count()
        interview_rate = round((interviews / shortlisted) * 100) if shortlisted else 0
        offer_rate = round((offers / interviews) * 100) if interviews else 0

        return {
            "by_status": status_bars,
            "by_month": month_bars,
            "by_company": company_bars,
            "by_domain": [
                ChartBar(label="IT Jobs", value=total, pct=100.0),
                ChartBar(label="Faculty Jobs", value=0, pct=0.0),
            ],
            "interview_success_rate": interview_rate,
            "offer_conversion_rate": offer_rate,
        }

    def _interview_tracker(self, applications, pu) -> list[InterviewTrackerItem]:
        items: list[InterviewTrackerItem] = []
        for app in applications:
            if app.status not in (
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplicationStatus.INTERVIEW_COMPLETED,
                JobApplicationStatus.OFFER_RELEASED,
                JobApplicationStatus.HIRED,
            ):
                continue
            detail = self._portal.get_detail(app.job_seeker, app.pk)
            if not detail or not detail.interview:
                continue
            inv = detail.interview
            state = (
                "upcoming"
                if app.status == JobApplicationStatus.INTERVIEW_SCHEDULED
                else "completed"
            )
            items.append(
                InterviewTrackerItem(
                    application_id=str(app.pk),
                    job_title=app.job_title_snapshot,
                    company_name=app.company_name_snapshot,
                    state=state,
                    interview_type=inv.interview_type,
                    date_label=inv.date_label,
                    time_label=inv.time_label,
                    meet_url=inv.meet_url,
                    panel=inv.panel,
                    instructions=inv.instructions,
                    countdown_label=inv.countdown_label,
                    detail_url=pu(
                        "jobseeker_application_detail", application_id=app.pk
                    ),
                )
            )
        return items[:10]

    def _offer_tracker(self, applications, pu) -> list[OfferTrackerItem]:
        items: list[OfferTrackerItem] = []
        for app in applications:
            if app.status not in (
                JobApplicationStatus.OFFER_RELEASED,
                JobApplicationStatus.OFFER_ACCEPTED,
                JobApplicationStatus.OFFER_DECLINED,
                JobApplicationStatus.HIRED,
            ):
                continue
            detail = self._portal.get_detail(app.job_seeker, app.pk)
            if not detail or not detail.offer:
                continue
            state = "pending"
            if (
                app.status == JobApplicationStatus.OFFER_ACCEPTED
                or app.status == JobApplicationStatus.HIRED
            ):
                state = "accepted"
            elif app.status == JobApplicationStatus.OFFER_DECLINED:
                state = "declined"
            off = detail.offer
            items.append(
                OfferTrackerItem(
                    application_id=str(app.pk),
                    job_title=app.job_title_snapshot,
                    company_name=app.company_name_snapshot,
                    state=state,
                    salary_display=off.salary_display,
                    joining_date=off.joining_date,
                    expiry_label=off.expiry_label,
                    letter_url=off.letter_url,
                    detail_url=pu(
                        "jobseeker_application_detail", application_id=app.pk
                    ),
                )
            )
        return items[:10]

    def _profile_insights(self, profile: JobSeekerProfile, pu) -> list[ProfileInsight]:
        completion = JobSeekerProfileCompletionService().get_dashboard_state(profile)
        insights: list[ProfileInsight] = []

        if completion.percentage < 100:
            insights.append(
                ProfileInsight(
                    key="completion",
                    message=f"Your profile is {completion.percentage}% complete. Complete remaining sections to improve recruiter visibility.",
                    action_label="Complete Profile",
                    action_url=pu("jobseeker_profile"),
                    tone="primary",
                )
            )

        for section in completion.sections:
            if not section.completed:
                insights.append(
                    ProfileInsight(
                        key=section.key,
                        message=f"Add your {section.label.lower()} to strengthen your recruiter profile.",
                        action_label=f"Add {section.label}",
                        action_url=pu("jobseeker_profile"),
                        tone="info",
                    )
                )

        skill_count = profile.skills.filter(is_deleted=False).count()
        if skill_count < 5:
            insights.append(
                ProfileInsight(
                    key="skills",
                    message=f"Add {5 - skill_count} more technical skills to improve job match accuracy.",
                    action_label="Update Skills",
                    action_url=pu("jobseeker_profile"),
                    tone="warning",
                )
            )

        if not profile.resume_file_id:
            insights.append(
                ProfileInsight(
                    key="resume",
                    message="Upload an updated resume so recruiters can evaluate your latest experience.",
                    action_label="Upload Resume",
                    action_url=pu("jobseeker_resume"),
                    tone="warning",
                )
            )

        return insights[:6]

    def _match_jobs(self, profile: JobSeekerProfile) -> list[MatchJobItem]:
        rows = (
            JobSeekerJobRecommendation.objects.filter(
                job_seeker=profile, is_deleted=False
            )
            .select_related("job_posting", "job_posting__company")
            .order_by("-match_score", "-computed_at")[:8]
        )
        items: list[MatchJobItem] = []
        for row in rows:
            job = row.job_posting
            items.append(
                MatchJobItem(
                    id=str(job.pk),
                    title=job.title,
                    company_name=job.company_name_snapshot or "",
                    match_percent=row.match_score,
                    detail_url=reverse(
                        "marketplace_job_detail", kwargs={"job_id": job.pk}
                    ),
                    is_new=row.is_new,
                )
            )
        if not items:
            snapshot = JobRecommendationCacheService().get_snapshot(profile)
            if snapshot and snapshot.top_match_job:
                job = snapshot.top_match_job
                items.append(
                    MatchJobItem(
                        id=str(job.pk),
                        title=job.title,
                        company_name=job.company_name_snapshot or "",
                        match_percent=snapshot.top_match_score,
                        detail_url=reverse(
                            "marketplace_job_detail", kwargs={"job_id": job.pk}
                        ),
                        is_new=False,
                    )
                )
        return items

    @staticmethod
    def _notif_icon(event_type: str) -> str:
        mapping = {
            "profile_viewed": "bi-eye-fill",
            "application.status_changed": "bi-arrow-repeat",
            "application.submitted": "bi-send-check",
            "job.recommended": "bi-stars",
        }
        return mapping.get(event_type, "bi-bell-fill")

    @staticmethod
    def _notif_tone(event_type: str) -> str:
        if "reject" in event_type:
            return "danger"
        if "offer" in event_type or "hire" in event_type:
            return "offer"
        if "interview" in event_type:
            return "interview"
        return "info"

    @staticmethod
    def _payload_str(payload, key: str, default: str = "") -> str:
        if isinstance(payload, dict):
            return str(payload.get(key) or default)
        return default

    @staticmethod
    def _payload_url(payload, pu) -> str | None:
        if isinstance(payload, dict) and payload.get("application_id"):
            return pu(
                "jobseeker_application_detail", application_id=payload["application_id"]
            )
        return None
