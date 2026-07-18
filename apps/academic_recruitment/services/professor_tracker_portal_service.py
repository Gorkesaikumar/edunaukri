"""Professor career tracker — faculty application pipeline and activity."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_dashboard_kpi_service import (
    ProfessorDashboardKPIService,
)
from apps.academic_recruitment.services.professor_portal_helpers import (
    faculty_status_ui,
    media_url,
)
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.academic_recruitment.services.professor_vacancy_recommendation_service import (
    ProfessorVacancyRecommendationService,
)
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.applications.constants.faculty_enums import (
    FACULTY_TERMINAL_STATUSES,
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)
from apps.applications.models import FacultyApplication, FacultyApplicationTimelineEvent
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.faculty.services.saved_vacancy_service import SavedVacancyService
from apps.notifications.models import Notification
from apps.applications.services.joining_status_resolver import JoiningStatusResolver

STATUS_RANK = {
    FacultyApplicationStatus.APPLIED: 1,
    FacultyApplicationStatus.UNDER_REVIEW: 2,
    FacultyApplicationStatus.SHORTLISTED: 3,
    FacultyApplicationStatus.ACADEMIC_VERIFICATION: 3,
    FacultyApplicationStatus.DEPARTMENT_REVIEW: 4,
    FacultyApplicationStatus.PRINCIPAL_REVIEW: 4,
    FacultyApplicationStatus.MANAGEMENT_APPROVAL: 4,
    FacultyApplicationStatus.INTERVIEW_SCHEDULED: 5,
    FacultyApplicationStatus.INTERVIEW_COMPLETED: 5,
    FacultyApplicationStatus.OFFER_RELEASED: 6,
    FacultyApplicationStatus.SELECTED: 6,
    FacultyApplicationStatus.OFFER_ACCEPTED: 7,
    FacultyApplicationStatus.JOINING_IN_PROGRESS: 7,
    FacultyApplicationStatus.JOINED: 8,
    FacultyApplicationStatus.REJECTED: 0,
    FacultyApplicationStatus.WITHDRAWN: 0,
    FacultyApplicationStatus.EXPIRED: 0,
    FacultyApplicationStatus.OFFER_DECLINED: 0,
}

PIPELINE_STAGE_DEFS = (
    ("applied", "Applied", 1, (FacultyApplicationStatus.APPLIED,), "bi-send-check"),
    (
        "reviewed",
        "Application Reviewed",
        2,
        (FacultyApplicationStatus.UNDER_REVIEW,),
        "bi-search",
    ),
    (
        "shortlisted",
        "Shortlisted",
        3,
        (FacultyApplicationStatus.SHORTLISTED,),
        "bi-check2-circle",
    ),
    (
        "interview_scheduled",
        "Interview Scheduled",
        5,
        (FacultyApplicationStatus.INTERVIEW_SCHEDULED,),
        "bi-calendar-event",
    ),
    (
        "interview_completed",
        "Interview Completed",
        5,
        (FacultyApplicationStatus.INTERVIEW_COMPLETED,),
        "bi-calendar2-check",
    ),
    (
        "selected",
        "Selected",
        6,
        (
            FacultyApplicationStatus.OFFER_RELEASED,
            FacultyApplicationStatus.OFFER_ACCEPTED,
            FacultyApplicationStatus.JOINED,
        ),
        "bi-award",
    ),
    (
        "offer_released",
        "Offer Released",
        6,
        (FacultyApplicationStatus.OFFER_RELEASED,),
        "bi-envelope-open",
    ),
    (
        "offer_accepted",
        "Offer Accepted",
        7,
        (FacultyApplicationStatus.OFFER_ACCEPTED,),
        "bi-hand-thumbs-up",
    ),
    ("joined", "Joined", 8, (FacultyApplicationStatus.JOINED,), "bi-trophy"),
)

TERMINAL_STAGE_ICONS = {
    FacultyApplicationStatus.REJECTED: "bi-x-octagon",
    FacultyApplicationStatus.WITHDRAWN: "bi-box-arrow-left",
    FacultyApplicationStatus.EXPIRED: "bi-hourglass-split",
    FacultyApplicationStatus.OFFER_DECLINED: "bi-hand-thumbs-down",
}


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
    state: str
    state_label: str
    icon: str
    timestamp: str
    recruiter_name: str
    description: str


@dataclass
class PipelineHistoryEntry:
    date: str
    time: str
    status_label: str
    updated_by: str
    remarks: str


@dataclass
class ApplicationPipeline:
    application_id: str
    job_title: str
    company_name: str
    logo_url: str | None
    department: str
    applied_date: str
    status: str
    status_label: str
    status_tone: str
    detail_url: str
    job_url: str
    interview_url: str | None
    offer_letter_url: str | None
    contact_email: str
    recruiter_name: str
    expected_next_step: str
    stages: list[PipelineStage]
    history: list[PipelineHistoryEntry]
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
    state: str
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
    state: str
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


class ProfessorTrackerPortalService(BaseService):
    """Aggregate faculty application tracker data for the professor portal."""

    def __init__(self):
        self._apps = FacultyApplicationSelector()
        self._stats = FacultyApplicationStatisticsService()

    def build(
        self,
        profile: ProfessorProfile,
        *,
        q: str = "",
        status: str = "",
        company: str = "",
        activity_page: int = 1,
        activity_page_size: int = 20,
    ) -> TrackerPageContext:
        kpis = ProfessorDashboardKPIService().build(profile)
        stats = self._stats.professor_dashboard(profile)
        by_status = stats.get("applications_by_status", {})
        active = stats.get("active_applications", 0)
        completion = ProfessorProfileCompletionService().get_dashboard_state(profile)

        applications = self._applications_qs(
            profile, q=q, status=status, company=company
        )
        user = profile.user
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        pipeline_apps = list(applications[:12])
        actor_lookup = self._actor_lookup(pipeline_apps)
        pipelines = [
            self._build_pipeline(app, pu, actor_lookup) for app in pipeline_apps
        ]
        match_jobs = self._match_jobs(profile, user)
        activities = self._build_activity_feed(profile, applications, pu, q=q)
        paginated = self._paginate_activities(
            activities, activity_page, activity_page_size
        )

        return TrackerPageContext(
            summary=self._summary_cards(
                profile, by_status, active, completion.percentage
            ),
            pipelines=pipelines,
            activities=paginated,
            profile_analytics=self._profile_analytics(
                profile=profile,
                kpis=kpis,
                by_status=by_status,
                completion_pct=completion.percentage,
                match_jobs=match_jobs,
            ),
            application_charts=self._application_charts(
                by_status, stats.get("total_applications", 0)
            ),
            interviews=self._interview_tracker(applications, pu),
            offers=self._offer_tracker(applications, pu),
            profile_insights=self._profile_insights(profile, completion, pu),
            match_jobs=match_jobs,
            match_score=completion.percentage,
            updated_at=timezone.localtime().strftime("%b %d, %Y · %I:%M %p"),
            filters={
                "q": q,
                "status": status,
                "company": company,
                "activity_page": activity_page,
            },
        )

    def export_csv(self, profile: ProfessorProfile) -> str:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        activities = self._build_activity_feed(
            profile, self._applications_qs(profile), pu
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "Date",
                "Time",
                "Title",
                "Institution",
                "Role",
                "Status",
                "Contact",
                "Source",
            ]
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
            self._apps.for_professor(profile)
            .select_related(
                "vacancy", "college", "vacancy__college", "vacancy__college__logo_file"
            )
            .prefetch_related("timeline")
        )
        if status:
            qs = qs.filter(status=status)
        if company:
            qs = qs.filter(college_name_snapshot__icontains=company)
        if q:
            qs = qs.filter(
                Q(vacancy_title_snapshot__icontains=q)
                | Q(college_name_snapshot__icontains=q)
            )
        return qs.order_by("-applied_at")

    def _summary_cards(
        self, profile, by_status: dict, active: int, completion_pct: int
    ) -> list[TrackerSummaryCard]:
        saved = SavedVacancyService().count(profile)
        cards = [
            (
                "applications",
                "Total Applications",
                sum(by_status.values()),
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
                by_status.get(FacultyApplicationStatus.UNDER_REVIEW, 0),
                "bi-eye-fill",
                "review",
            ),
            (
                "shortlisted",
                "Shortlisted",
                sum(
                    by_status.get(s, 0)
                    for s in (
                        FacultyApplicationStatus.SHORTLISTED,
                        FacultyApplicationStatus.DEPARTMENT_REVIEW,
                        FacultyApplicationStatus.PRINCIPAL_REVIEW,
                        FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                    )
                ),
                "bi-star-fill",
                "success",
            ),
            (
                "interviews",
                "Interviews Scheduled",
                by_status.get(FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0),
                "bi-calendar-event-fill",
                "interview",
            ),
            (
                "offers",
                "Offers Received",
                by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0),
                "bi-envelope-open-heart-fill",
                "offer",
            ),
            (
                "joined",
                "Selected",
                by_status.get(FacultyApplicationStatus.JOINED, 0),
                "bi-trophy-fill",
                "hired",
            ),
            (
                "rejected",
                "Rejected",
                by_status.get(FacultyApplicationStatus.REJECTED, 0),
                "bi-x-circle-fill",
                "danger",
            ),
            ("saved", "Saved Jobs", saved, "bi-bookmark-fill", "primary"),
            (
                "completion",
                "Profile Completion",
                completion_pct,
                "bi-person-check-fill",
                "success",
            ),
        ]
        return [
            TrackerSummaryCard(
                key=key,
                label=label,
                value=f"{value}%" if key == "completion" else str(value),
                raw_value=value,
                icon=icon,
                tone=tone,
            )
            for key, label, value, icon, tone in cards
        ]

    def _build_pipeline(
        self, app: FacultyApplication, pu, actor_lookup: dict[tuple[str, str], str]
    ) -> ApplicationPipeline:
        rank = STATUS_RANK.get(app.status, 0)
        timeline_events = sorted(app.timeline.all(), key=lambda e: e.occurred_at)
        recruiter_name = "Institution Recruiter"
        current_status_label, current_status_tone = faculty_status_ui(app.status)
        latest_offer_event = next(
            (
                event
                for event in reversed(timeline_events)
                if event.event_type == FacultyTimelineEventType.OFFER
            ),
            None,
        )
        offer_meta = (latest_offer_event.metadata if latest_offer_event else {}) or {}

        stages: list[PipelineStage] = []
        current_index = 0
        for idx, (key, label, min_rank, statuses, icon) in enumerate(
            PIPELINE_STAGE_DEFS
        ):
            if app.status in FACULTY_TERMINAL_STATUSES and app.status not in (
                FacultyApplicationStatus.JOINED,
                FacultyApplicationStatus.OFFER_ACCEPTED,
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

            event = self._stage_event_for_statuses(timeline_events, statuses)
            ts = desc = ""
            stage_actor = ""
            if event:
                when = timezone.localtime(event.occurred_at)
                ts = when.strftime("%b %d, %Y · %I:%M %p")
                desc = event.notes or ""
                stage_actor = self._event_actor_name(event, actor_lookup)
            elif key == "applied":
                when = timezone.localtime(app.applied_at)
                ts = when.strftime("%b %d, %Y · %I:%M %p")
                desc = "Application submitted successfully."
                stage_actor = "You"

            resolved_state = (
                "current" if idx == current_index and state != "completed" else state
            )
            state_label = {
                "completed": "Completed",
                "current": "Current Stage",
                "pending": "Upcoming",
                "skipped": "Not Reached",
                "rejected": "Rejected",
            }.get(resolved_state, "Pending")
            stages.append(
                PipelineStage(
                    key=key,
                    label=label,
                    state=resolved_state,
                    state_label=state_label,
                    icon=icon,
                    timestamp=ts,
                    recruiter_name=stage_actor or recruiter_name,
                    description=desc,
                )
            )

        if (
            app.status in TERMINAL_STAGE_ICONS
            and app.status != FacultyApplicationStatus.JOINED
        ):
            stages.append(
                PipelineStage(
                    key="terminal",
                    label=current_status_label,
                    state="rejected",
                    state_label="Rejected",
                    icon=TERMINAL_STAGE_ICONS[app.status],
                    timestamp="",
                    recruiter_name=recruiter_name,
                    description="This application ended before joining.",
                )
            )

        college = app.college or (app.vacancy.college if app.vacancy_id else None)
        logo = (
            media_url(college.logo_file)
            if college and getattr(college, "logo_file_id", None)
            else None
        )
        history = self._pipeline_history(timeline_events, actor_lookup)

        return ApplicationPipeline(
            application_id=str(app.pk),
            job_title=app.vacancy_title_snapshot,
            company_name=app.college_name_snapshot or "Institution",
            logo_url=logo,
            department=getattr(app, "department_snapshot", "")
            or getattr(app.vacancy, "department", "")
            or "Department not specified",
            applied_date=timezone.localtime(app.applied_at).strftime("%b %d, %Y"),
            status=app.status,
            status_label=current_status_label,
            status_tone=self._status_tone(current_status_tone),
            detail_url=pu("professor_application_detail", application_id=app.pk),
            job_url=pu("professor_vacancy_detail", vacancy_id=app.vacancy_id)
            if app.vacancy_id
            else "",
            interview_url=(
                pu("professor_interview_detail", application_id=app.pk)
                if app.status
                in (
                    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                    FacultyApplicationStatus.INTERVIEW_COMPLETED,
                )
                else None
            ),
            offer_letter_url=offer_meta.get("offer_letter_url")
            or offer_meta.get("letter_url"),
            contact_email=getattr(college, "contact_email", "") or "",
            recruiter_name=recruiter_name,
            expected_next_step=self._expected_next_step(app.status),
            stages=stages,
            history=history,
            current_index=current_index,
        )

    @staticmethod
    def _stage_event_for_statuses(
        events: list[FacultyApplicationTimelineEvent], statuses: tuple[str, ...]
    ):
        for event in reversed(events):
            if event.to_status in statuses:
                return event
        return None

    @staticmethod
    def _event_actor_name(
        event: FacultyApplicationTimelineEvent, actor_lookup: dict[tuple[str, str], str]
    ) -> str:
        if event.actor_id and event.actor_domain:
            return actor_lookup.get((event.actor_domain, str(event.actor_id)), "")
        return "System"

    def _actor_lookup(
        self, applications: list[FacultyApplication]
    ) -> dict[tuple[str, str], str]:
        college_ids: set[str] = set()
        professor_ids: set[str] = set()
        for app in applications:
            for event in app.timeline.all():
                if not event.actor_id or not event.actor_domain:
                    continue
                if event.actor_domain == "college":
                    college_ids.add(str(event.actor_id))
                elif event.actor_domain == "professor":
                    professor_ids.add(str(event.actor_id))

        mapping: dict[tuple[str, str], str] = {}
        if college_ids:
            for user in CollegeUser.objects.filter(pk__in=list(college_ids)).only(
                "pk", "email"
            ):
                display = user.email.split("@")[0]
                mapping[("college", str(user.pk))] = display.replace(".", " ").title()
        if professor_ids:
            for user in ProfessorUser.objects.filter(pk__in=list(professor_ids)).only(
                "pk", "email"
            ):
                display = user.email.split("@")[0]
                mapping[("professor", str(user.pk))] = display.replace(".", " ").title()
        return mapping

    def _pipeline_history(
        self,
        timeline_events: list[FacultyApplicationTimelineEvent],
        actor_lookup: dict[tuple[str, str], str],
    ) -> list[PipelineHistoryEntry]:
        history: list[PipelineHistoryEntry] = []
        for event in reversed(timeline_events):
            when = timezone.localtime(event.occurred_at)
            label, _ = faculty_status_ui(event.to_status or "")
            history.append(
                PipelineHistoryEntry(
                    date=when.strftime("%b %d, %Y"),
                    time=when.strftime("%I:%M %p"),
                    status_label=label or "Status Updated",
                    updated_by=self._event_actor_name(event, actor_lookup) or "System",
                    remarks=event.notes or "",
                )
            )
        return history

    @staticmethod
    def _expected_next_step(status: str) -> str:
        next_step = {
            FacultyApplicationStatus.APPLIED: "Await application review from institution.",
            FacultyApplicationStatus.UNDER_REVIEW: "Your application is being reviewed by the institution.",
            FacultyApplicationStatus.SHORTLISTED: "Congratulations! You have been shortlisted. Expect an interview invitation soon.",
            FacultyApplicationStatus.ACADEMIC_VERIFICATION: "Academic credentials are being verified.",
            FacultyApplicationStatus.DEPARTMENT_REVIEW: "Institution management decision pending.",
            FacultyApplicationStatus.PRINCIPAL_REVIEW: "Institution management decision pending.",
            FacultyApplicationStatus.MANAGEMENT_APPROVAL: "Interview scheduling may follow.",
            FacultyApplicationStatus.INTERVIEW_SCHEDULED: "Attend interview and await completion update.",
            FacultyApplicationStatus.INTERVIEW_COMPLETED: "Selection decision is pending.",
            FacultyApplicationStatus.SELECTED: "You have been selected. Joining in progress.",
            FacultyApplicationStatus.JOINING_IN_PROGRESS: "Joining formalities are in progress.",
            FacultyApplicationStatus.OFFER_RELEASED: "Review and respond to offer.",
            FacultyApplicationStatus.OFFER_ACCEPTED: "Joining formalities are in progress.",
            FacultyApplicationStatus.JOINED: "Onboarding completed.",
            FacultyApplicationStatus.REJECTED: "Application closed by institution.",
            FacultyApplicationStatus.WITHDRAWN: "Application withdrawn by candidate.",
            FacultyApplicationStatus.EXPIRED: "Application expired.",
            FacultyApplicationStatus.OFFER_DECLINED: "Offer declined.",
        }
        return next_step.get(status, "Await institution update.")

    @staticmethod
    def _status_tone(status_css: str) -> str:
        if "danger" in status_css:
            return "rejected"
        if "success" in status_css:
            return "shortlisted"
        if "info" in status_css:
            return "review"
        return "applied"

    def _build_activity_feed(
        self, profile, applications, pu, q=""
    ) -> list[ActivityFeedItem]:
        items: list[ActivityFeedItem] = []
        cutoff = timezone.now() - timedelta(days=90)

        for notif in Notification.objects.filter(
            recipient_domain="professor",
            recipient_id=profile.user_id,
            created_at__gte=cutoff,
        ).order_by("-created_at")[:40]:
            when = timezone.localtime(notif.created_at)
            items.append(
                ActivityFeedItem(
                    id=f"n-{notif.pk}",
                    icon="bi-bell",
                    tone="info",
                    title=notif.title or "Update",
                    subtitle=notif.body or "",
                    company=self._payload_str(
                        notif.payload, "college_name", "institution_name"
                    ),
                    job_title=self._payload_str(
                        notif.payload, "vacancy_title", "job_title"
                    ),
                    status_label=(notif.event_type or "")
                    .replace(".", " ")
                    .replace("_", " ")
                    .title(),
                    recruiter_name=self._payload_str(
                        notif.payload, "recruiter_name", "Institution"
                    ),
                    occurred_date=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                    detail_url=self._payload_url(notif.payload, pu),
                    source="notification",
                )
            )

        app_ids = list(applications.values_list("pk", flat=True)[:50])
        for event in (
            FacultyApplicationTimelineEvent.objects.filter(
                application_id__in=app_ids, occurred_at__gte=cutoff
            )
            .select_related("application")
            .order_by("-occurred_at")[:60]
        ):
            app = event.application
            when = timezone.localtime(event.occurred_at)
            title, desc, icon, tone = self._timeline_ui(event)
            status_label, _ = faculty_status_ui(app.status)
            items.append(
                ActivityFeedItem(
                    id=f"t-{event.pk}",
                    icon=icon,
                    tone=tone,
                    title=title,
                    subtitle=event.notes or desc,
                    company=app.college_name_snapshot or "Institution",
                    job_title=app.vacancy_title_snapshot,
                    status_label=status_label,
                    recruiter_name="Institution Recruiter",
                    occurred_date=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                    detail_url=pu(
                        "professor_application_detail", application_id=app.pk
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
    def _timeline_ui(
        event: FacultyApplicationTimelineEvent,
    ) -> tuple[str, str, str, str]:
        if event.event_type == FacultyTimelineEventType.WITHDRAW:
            return "Application withdrawn", "", "bi-box-arrow-left", "muted"
        if event.event_type == FacultyTimelineEventType.OFFER:
            return (
                "Offer update",
                "Offer status changed.",
                "bi-envelope-open",
                "success",
            )
        if event.event_type == FacultyTimelineEventType.JOINED:
            return (
                "Joined institution",
                "Congratulations on joining.",
                "bi-trophy",
                "success",
            )
        if event.event_type == FacultyTimelineEventType.REJECT:
            return "Application update", "Status changed.", "bi-x-circle", "danger"
        if event.to_status == FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            return (
                "Interview scheduled",
                "Your interview has been scheduled.",
                "bi-calendar-event",
                "info",
            )
        return (
            "Status updated",
            "Application progress updated.",
            "bi-arrow-repeat",
            "info",
        )

    @staticmethod
    def _payload_str(payload, *keys, default=""):
        if not isinstance(payload, dict):
            return default
        for key in keys:
            if payload.get(key):
                return str(payload[key])
        return default

    @staticmethod
    def _payload_url(payload, pu):
        if not isinstance(payload, dict):
            return None
        app_id = payload.get("application_id")
        if app_id:
            return pu("professor_application_detail", application_id=app_id)
        return None

    @staticmethod
    def _paginate_activities(
        items: list[ActivityFeedItem], page: int, page_size: int
    ) -> list[ActivityFeedItem]:
        start = (max(1, page) - 1) * page_size
        return items[start : start + page_size]

    def _profile_analytics(
        self,
        *,
        profile: ProfessorProfile,
        kpis,
        by_status: dict,
        completion_pct: int,
        match_jobs: list[MatchJobItem],
    ) -> dict:
        week_start = timezone.now() - timedelta(days=7)
        views_this_week = Notification.objects.filter(
            recipient_domain="professor",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
            created_at__gte=week_start,
        ).count()
        applications_submitted = sum(by_status.values())
        interviews_scheduled = by_status.get(
            FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0
        )
        offers_received = by_status.get(
            FacultyApplicationStatus.OFFER_RELEASED, 0
        ) + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0)
        responded = applications_submitted - by_status.get(
            FacultyApplicationStatus.APPLIED, 0
        )
        response_rate = (
            round((responded / applications_submitted) * 100)
            if applications_submitted
            else 0
        )
        avg_match = (
            round(
                sum(job.match_percent for job in match_jobs) / max(len(match_jobs), 1)
            )
            if match_jobs
            else completion_pct
        )
        return {
            "profile_views": kpis.profile_views_total,
            "profile_views_today": kpis.profile_views_today,
            "views_this_week": views_this_week,
            "visibility_change": kpis.profile_visibility_change,
            "recruiter_interest": kpis.institution_interest_score,
            "skills_match_percentage": avg_match,
            "applications_submitted": applications_submitted,
            "interviews_scheduled": interviews_scheduled,
            "offers_received": offers_received,
            "response_rate": response_rate,
            "profile_completion": completion_pct,
            # Backward compatible keys for existing template/API consumers.
            "skills_matched": len(match_jobs),
            "missing_skills": max(0, 5 - len(match_jobs)),
            "avg_match_score": avg_match,
        }

    @staticmethod
    def _application_charts(by_status: dict, total: int) -> dict:
        labels = [
            ("Applied", FacultyApplicationStatus.APPLIED),
            ("Under Review", FacultyApplicationStatus.UNDER_REVIEW),
            ("Shortlisted", FacultyApplicationStatus.DEPARTMENT_REVIEW),
            ("Interview", FacultyApplicationStatus.INTERVIEW_SCHEDULED),
            ("Offer", FacultyApplicationStatus.OFFER_RELEASED),
            ("Selected", FacultyApplicationStatus.JOINED),
        ]
        bars = []
        for label, status in labels:
            value = by_status.get(status, 0)
            pct = round((value / total) * 100, 1) if total else 0
            bars.append(ChartBar(label=label, value=value, pct=pct))
        interviews = by_status.get(FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0)
        completed = by_status.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0)
        interview_rate = round((completed / interviews) * 100) if interviews else 0
        offers = by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
        offer_rate = round((offers / max(completed, 1)) * 100) if completed else 0
        return {
            "by_status": bars,
            "interview_success_rate": interview_rate,
            "offer_conversion_rate": offer_rate,
        }

    def _interview_tracker(self, applications, pu) -> list[InterviewTrackerItem]:
        from apps.academic_recruitment.services.professor_interview_portal_service import (
            ProfessorInterviewPortalService,
        )

        items: list[InterviewTrackerItem] = []
        for app in applications.filter(
            status__in=(
                FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                FacultyApplicationStatus.INTERVIEW_COMPLETED,
            )
        )[:8]:
            meta = ProfessorInterviewPortalService._interview_meta(app)
            dt = meta.get("datetime")
            now = timezone.now()
            state = (
                "upcoming"
                if app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED
                and dt
                and dt >= now
                else "completed"
            )
            countdown = None
            if state == "upcoming" and dt:
                delta = dt - now
                if delta.total_seconds() > 0:
                    hours = int(delta.total_seconds() // 3600)
                    countdown = f"In {hours}h" if hours else "Starting soon"
            items.append(
                InterviewTrackerItem(
                    application_id=str(app.pk),
                    job_title=app.vacancy_title_snapshot,
                    company_name=app.college_name_snapshot or "Institution",
                    state=state,
                    interview_type=meta.get("interview_type") or "Interview",
                    date_label=dt.strftime("%b %d, %Y") if dt else "TBD",
                    time_label=dt.strftime("%I:%M %p").lstrip("0") if dt else "",
                    meet_url=meta.get("meet_url"),
                    panel=meta.get("panel_lead") or "",
                    instructions=meta.get("instructions") or "",
                    countdown_label=countdown,
                    detail_url=pu("professor_interview_detail", application_id=app.pk),
                )
            )
        return items

    @staticmethod
    def _offer_tracker(applications, pu) -> list[OfferTrackerItem]:
        items: list[OfferTrackerItem] = []
        for app in applications.filter(
            status__in=(
                FacultyApplicationStatus.OFFER_RELEASED,
                FacultyApplicationStatus.OFFER_ACCEPTED,
                FacultyApplicationStatus.OFFER_DECLINED,
                FacultyApplicationStatus.JOINING_IN_PROGRESS,
                FacultyApplicationStatus.JOINED,
            )
        )[:8]:
            event = (
                app.timeline.filter(event_type=FacultyTimelineEventType.OFFER)
                .order_by("-occurred_at")
                .first()
            )
            meta = (event.metadata if event else {}) or {}
            state = "pending"
            if app.status == FacultyApplicationStatus.OFFER_ACCEPTED:
                state = "accepted"
            elif app.status == FacultyApplicationStatus.OFFER_DECLINED:
                state = "declined"
            elif app.status == FacultyApplicationStatus.JOINING_IN_PROGRESS:
                state = "joining"
            elif app.status == FacultyApplicationStatus.JOINED:
                state = "joined"

            # Use centralized resolver
            joining_label, joining_date_str = JoiningStatusResolver.resolve_faculty(
                app, offer_meta=meta
            )
            joining_display = JoiningStatusResolver.joining_display(joining_label, joining_date_str)

            items.append(
                OfferTrackerItem(
                    application_id=str(app.pk),
                    job_title=app.vacancy_title_snapshot,
                    company_name=app.college_name_snapshot or "Institution",
                    state=state,
                    salary_display=meta.get("salary_display")
                    or meta.get("salary")
                    or "As per institution policy",
                    joining_date=joining_display,
                    expiry_label=meta.get("expiry_label"),
                    letter_url=meta.get("offer_letter_url") or meta.get("letter_url"),
                    detail_url=pu(
                        "professor_application_detail", application_id=app.pk
                    ),
                )
            )
        return items

    @staticmethod
    def _profile_insights(profile, completion, pu) -> list[ProfileInsight]:
        items: list[ProfileInsight] = []
        profile_url = pu("professor_profile")
        if completion.percentage < 100:
            for item in completion.checklist:
                if not item.completed:
                    items.append(
                        ProfileInsight(
                            key=item.key,
                            message=f"Complete {item.label.lower()} to improve visibility to institutions.",
                            action_label="Update profile",
                            action_url=item.url or profile_url,
                            tone="info",
                        )
                    )
                    if len(items) >= 3:
                        break
        if not profile.cv_file_id:
            items.append(
                ProfileInsight(
                    key="cv",
                    message="Upload your CV to strengthen faculty applications.",
                    action_label="Upload CV",
                    action_url=pu("professor_resume"),
                    tone="primary",
                )
            )
        return items[:4]

    @staticmethod
    def _match_jobs(profile, user) -> list[MatchJobItem]:
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        items: list[MatchJobItem] = []
        for vacancy in ProfessorVacancyRecommendationService().recommend(
            profile, limit=5
        ):
            college = vacancy.college
            score = 70 + (10 if vacancy.is_featured else 0)
            items.append(
                MatchJobItem(
                    id=str(vacancy.pk),
                    title=vacancy.title,
                    company_name=college.name
                    if college
                    else vacancy.college_name_snapshot,
                    match_percent=min(score, 99),
                    detail_url=pu("professor_vacancy_detail", vacancy_id=vacancy.pk),
                    is_new=bool(vacancy.is_featured),
                )
            )
        return items
