"""Job seeker interview command center — list, detail, analytics, and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService

from apps.applications.constants.enums import JobApplicationStatus, TimelineEventType
from apps.applications.constants.interview_enums import InterviewStatus
from apps.applications.models import JobApplication
from apps.applications.selectors.application_selector import JobApplicationSelector
from apps.applications.selectors.timeline_selector import JobApplicationTimelineSelector
from apps.applications.services.application_history_service import (
    ApplicationHistoryService,
)
from apps.applications.services.interview_scheduling_service import (
    InterviewSchedulingService,
    InterviewSelector,
)
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_application_portal_service import (
    JobSeekerApplicationPortalService,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import media_url
from apps.reports.selectors.featured_jobs import FeaturedJobsSelector

JOIN_WINDOW_MINUTES = 15
INTERVIEW_APP_STATUSES = (
    JobApplicationStatus.SHORTLISTED,
    JobApplicationStatus.INTERVIEW_SCHEDULED,
    JobApplicationStatus.INTERVIEW_COMPLETED,
    JobApplicationStatus.OFFER_RELEASED,
    JobApplicationStatus.OFFER_ACCEPTED,
    JobApplicationStatus.OFFER_DECLINED,
    JobApplicationStatus.HIRED,
    JobApplicationStatus.REJECTED,
)

INTERVIEW_STATUS_UI = {
    "scheduled": (
        "Interview Scheduled",
        "jsd-int-badge--scheduled",
        "bi-calendar-event",
        "Your interview has been scheduled.",
    ),
    "confirmed": (
        "Interview Confirmed",
        "jsd-int-badge--confirmed",
        "bi-check-circle-fill",
        "You confirmed your attendance.",
    ),
    "waiting": (
        "Waiting for Candidate",
        "jsd-int-badge--waiting",
        "bi-hourglass-split",
        "Please confirm your availability.",
    ),
    "in_progress": (
        "Interview In Progress",
        "jsd-int-badge--live",
        "bi-broadcast",
        "Your interview is in progress.",
    ),
    "completed": (
        "Interview Completed",
        "jsd-int-badge--completed",
        "bi-check2-all",
        "This interview round is complete.",
    ),
    "rescheduled": (
        "Rescheduled",
        "jsd-int-badge--rescheduled",
        "bi-arrow-repeat",
        "Interview timing was updated.",
    ),
    "cancelled": (
        "Cancelled",
        "jsd-int-badge--cancelled",
        "bi-x-circle",
        "This interview was cancelled.",
    ),
    "shortlisted": (
        "Shortlisted",
        "jsd-int-badge--shortlisted",
        "bi-star-fill",
        "Awaiting interview schedule.",
    ),
    "offer": (
        "Offer Released",
        "jsd-int-badge--offer",
        "bi-envelope-open-heart",
        "Offer released after interview process.",
    ),
    "hired": (
        "Hired",
        "jsd-int-badge--hired",
        "bi-trophy-fill",
        "Congratulations — you have been hired.",
    ),
    "rejected": (
        "Rejected",
        "jsd-int-badge--rejected",
        "bi-x-octagon",
        "Not selected after interview process.",
    ),
}


@dataclass
class InterviewSummaryCard:
    key: str
    label: str
    value: int
    icon: str
    tone: str


@dataclass
class PanelMember:
    name: str
    designation: str
    department: str


@dataclass
class InterviewListCard:
    application_id: str
    interview_id: str
    job_title: str
    company_name: str
    company_verified: bool
    logo_url: str | None
    logo_initial: str
    domain_label: str
    round_label: str
    interview_type: str
    mode: str
    date_label: str
    time_label: str
    timezone_label: str
    duration_label: str
    status_key: str
    status_label: str
    status_badge: str
    status_icon: str
    recruiter_name: str
    recruiter_avatar: str | None
    scheduled_at_iso: str
    meet_url: str | None
    can_join: bool
    detail_url: str
    is_today: bool
    is_upcoming: bool


@dataclass
class InterviewTimelineEntry:
    title: str
    description: str
    actor_name: str
    occurred_date: str
    occurred_time: str
    icon: str
    tone: str


@dataclass
class InterviewFeedback:
    visible: bool
    technical: str | None
    communication: str | None
    problem_solving: str | None
    overall: str | None
    comments: str | None
    confidential_message: str


@dataclass
class RecruiterUpdate:
    message: str
    recruiter_name: str
    occurred_date: str
    occurred_time: str


@dataclass
class InterviewDetailContext:
    application_id: str
    interview_id: str
    status_key: str
    status_label: str
    status_badge: str
    status_icon: str
    status_description: str
    round_label: str
    interview_type: str
    mode: str
    date_label: str
    time_label: str
    timezone_label: str
    duration_label: str
    scheduled_at_iso: str
    meet_url: str | None
    can_join: bool
    can_confirm: bool
    can_reschedule: bool
    instructions: str
    required_documents: list[str]
    job_title: str
    company_name: str
    company_verified: bool
    company_profile_url: str | None
    department: str
    salary_display: str | None
    employment_type: str
    work_mode: str
    location: str
    recruiter_name: str
    recruiter_designation: str
    recruiter_avatar: str | None
    recruiter_email: str
    panel: list[PanelMember]
    timeline: list[InterviewTimelineEntry] = field(default_factory=list)
    recruiter_updates: list[RecruiterUpdate] = field(default_factory=list)
    feedback: InterviewFeedback | None = None
    calendar_url: str = ""
    countdown_seconds: int | None = None


@dataclass
class InterviewListResult:
    interviews: list[InterviewListCard]
    summary: list[InterviewSummaryCard]
    analytics: dict
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters: dict


class JobSeekerInterviewPortalService(BaseService):
    """Interview management portal built on application timeline metadata."""

    def __init__(self):
        self._apps = JobApplicationSelector()
        self._timeline = JobApplicationTimelineSelector()
        self._portal = JobSeekerApplicationPortalService()
        self._mapper = FeaturedJobsSelector()
        self._history = ApplicationHistoryService()
        self._interviews = InterviewSelector()
        self._scheduling = InterviewSchedulingService()

    def list_interviews(
        self,
        profile: JobSeekerProfile,
        *,
        page: int = 1,
        page_size: int = 10,
        q: str = "",
        status_filter: str = "",
        when: str = "",
        company: str = "",
        mode: str = "",
    ) -> InterviewListResult:
        qs = self._interview_queryset(profile, q=q, company=company, mode=mode)
        user = profile.user
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        cards = [self._map_list_card(app, pu) for app in qs]
        cards = self._apply_filters(cards, status_filter=status_filter, when=when)

        paginator = Paginator(cards, page_size)
        page_obj = paginator.get_page(page)
        summary = self._summary_cards(cards)
        analytics = self._analytics(cards)

        return InterviewListResult(
            interviews=list(page_obj.object_list),
            summary=summary,
            analytics=analytics,
            total_count=paginator.count,
            page=page_obj.number,
            page_size=page_size,
            total_pages=paginator.num_pages,
            filters={
                "q": q,
                "status": status_filter,
                "when": when,
                "company": company,
                "mode": mode,
            },
        )

    def get_detail(
        self, profile: JobSeekerProfile, application_id
    ) -> InterviewDetailContext | None:
        app = (
            self._apps.for_seeker(profile)
            .filter(pk=application_id)
            .select_related(
                "job_posting",
                "job_posting__company",
                "job_posting__posted_by",
                "job_posting__posted_by__profile_image",
            )
            .prefetch_related("timeline")
            .first()
        )
        if not app or app.status not in INTERVIEW_APP_STATUSES:
            return None
        return self._map_detail(app)

    def confirm_attendance(
        self, profile: JobSeekerProfile, application_id, *, actor
    ) -> None:
        app = self._apps.for_seeker(profile).filter(pk=application_id).first()
        if not app:
            raise ValueError("Interview not found.")
        interview = self._interviews.latest_for_application(app)
        if interview and interview.status not in (
            InterviewStatus.CANCELLED,
            InterviewStatus.COMPLETED,
        ):
            self._scheduling.confirm_by_candidate(interview, actor=actor)
            return
        if app.status != JobApplicationStatus.INTERVIEW_SCHEDULED:
            raise ValueError("Only scheduled interviews can be confirmed.")
        self._history.record_comment(
            app,
            notes="Candidate confirmed interview attendance.",
            event_type=TimelineEventType.CANDIDATE_ACTION,
            actor_id=getattr(actor, "pk", None),
        )

    def request_reschedule(
        self, profile: JobSeekerProfile, application_id, *, actor, reason: str = ""
    ) -> None:
        app = self._apps.for_seeker(profile).filter(pk=application_id).first()
        if not app:
            raise ValueError("Interview not found.")
        interview = self._interviews.latest_for_application(app)
        if interview:
            self._scheduling.request_reschedule_by_candidate(
                interview, actor=actor, reason=reason
            )
            return
        if app.status not in (
            JobApplicationStatus.INTERVIEW_SCHEDULED,
            JobApplicationStatus.SHORTLISTED,
        ):
            raise ValueError("Reschedule is not available for this interview.")
        note = reason.strip() or "Candidate requested a reschedule."
        self._history.record_comment(
            app,
            notes=f"Reschedule requested: {note}",
            event_type=TimelineEventType.CANDIDATE_ACTION,
            actor_id=getattr(actor, "pk", None),
        )

    def _interview_queryset(self, profile, *, q="", company="", mode=""):
        qs = (
            self._apps.for_seeker(profile)
            .filter(status__in=INTERVIEW_APP_STATUSES)
            .select_related(
                "job_posting",
                "job_posting__company",
                "job_posting__company__logo_file",
                "job_posting__posted_by",
                "job_posting__posted_by__profile_image",
            )
            .prefetch_related("timeline")
            .order_by("-status_changed_at")
        )
        if company:
            qs = qs.filter(company_name_snapshot__icontains=company)
        if q:
            qs = qs.filter(
                Q(job_title_snapshot__icontains=q)
                | Q(company_name_snapshot__icontains=q)
                | Q(job_posting__posted_by__first_name__icontains=q)
                | Q(job_posting__posted_by__last_name__icontains=q)
            )
        return qs

    def _map_list_card(self, app: JobApplication, pu) -> InterviewListCard:
        meta, scheduled_at = self._interview_meta(app)
        recruiter = app.job_posting.posted_by if app.job_posting_id else None
        company = app.job_posting.company if app.job_posting_id else None
        org = app.company_name_snapshot or (company.name if company else "")
        when = timezone.localtime(scheduled_at)
        now = timezone.localtime()
        status_key = self._resolve_status_key(app, meta)
        ui = INTERVIEW_STATUS_UI[status_key]

        return InterviewListCard(
            application_id=str(app.pk),
            interview_id=meta.get("interview_id") or str(app.pk),
            job_title=app.job_title_snapshot,
            company_name=org,
            company_verified=True,
            logo_url=media_url(company.logo_file)
            if company and company.logo_file
            else None,
            logo_initial=(org[:1] or "E").upper(),
            domain_label="IT Domain",
            round_label=meta.get(
                "round_label", meta.get("interview_round", "Interview Round")
            ),
            interview_type=meta.get("interview_type", "Technical Interview"),
            mode=meta.get("mode", meta.get("interview_mode", "Online")),
            date_label=when.strftime("%b %d, %Y"),
            time_label=when.strftime("%I:%M %p"),
            timezone_label=meta.get("timezone", "IST"),
            duration_label=meta.get("duration", meta.get("duration_minutes", "45 min")),
            status_key=status_key,
            status_label=ui[0],
            status_badge=ui[1],
            status_icon=ui[2],
            recruiter_name=recruiter.full_name if recruiter else "Recruiting Team",
            recruiter_avatar=media_url(recruiter.profile_image)
            if recruiter and recruiter.profile_image
            else None,
            scheduled_at_iso=when.isoformat(),
            meet_url=meta.get("meet_url") or meta.get("meeting_link"),
            can_join=self._can_join(app, scheduled_at, meta),
            detail_url=pu("jobseeker_interview_detail", application_id=app.pk),
            is_today=when.date() == now.date(),
            is_upcoming=app.status == JobApplicationStatus.INTERVIEW_SCHEDULED
            and when >= now,
        )

    def _map_detail(self, app: JobApplication) -> InterviewDetailContext:
        meta, scheduled_at = self._interview_meta(app)
        job = app.job_posting
        company = job.company if job else None
        recruiter = job.posted_by if job else None
        status_key = self._resolve_status_key(app, meta)
        ui = INTERVIEW_STATUS_UI[status_key]
        when = timezone.localtime(scheduled_at)
        inv = self._portal._extract_interview(app, list(app.timeline.all()))
        location = (
            self._mapper._location(city=job.city, state=job.state, remote=job.is_remote, fallback=job.location)
            if job
            else ""
        )

        panel_raw = (
            meta.get("panel_members")
            or meta.get("interviewers")
            or meta.get("panel")
            or []
        )
        panel = self._parse_panel(panel_raw, meta)

        timeline = self._interview_timeline(app)
        updates = self._recruiter_updates(app)
        feedback = self._feedback(meta)

        company_slug = company.slug if company else None
        return InterviewDetailContext(
            application_id=str(app.pk),
            interview_id=meta.get("interview_id") or str(app.pk),
            status_key=status_key,
            status_label=ui[0],
            status_badge=ui[1],
            status_icon=ui[2],
            status_description=ui[3],
            round_label=meta.get(
                "round_label", meta.get("interview_round", "Interview Round")
            ),
            interview_type=meta.get("interview_type", "Technical Interview"),
            mode=meta.get("mode", meta.get("interview_mode", "Online")),
            date_label=when.strftime("%A, %b %d, %Y"),
            time_label=when.strftime("%I:%M %p"),
            timezone_label=meta.get("timezone", "IST"),
            duration_label=str(
                meta.get("duration", meta.get("duration_minutes", "45 min"))
            ),
            scheduled_at_iso=when.isoformat(),
            meet_url=(inv.meet_url if inv else None)
            or meta.get("meet_url")
            or meta.get("meeting_link"),
            can_join=self._can_join(app, scheduled_at, meta),
            can_confirm=(
                app.status == JobApplicationStatus.INTERVIEW_SCHEDULED
                and not meta.get("confirmed")
                and not meta.get("candidate_confirmed")
            ),
            can_reschedule=app.status
            in (
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplicationStatus.SHORTLISTED,
            ),
            instructions=(inv.instructions if inv else "")
            or meta.get("instructions", ""),
            required_documents=meta.get("required_documents")
            or meta.get("documents")
            or [],
            job_title=app.job_title_snapshot,
            company_name=app.company_name_snapshot,
            company_verified=True,
            company_profile_url=(
                reverse("institution_detail", kwargs={"slug": company_slug})
                if company_slug
                else None
            ),
            department=job.department if job else "",
            salary_display=self._mapper._salary(
                job.salary_min, job.salary_max, job.salary_visibility
            )
            if job
            else None,
            employment_type=job.get_employment_type_display() if job else "",
            work_mode=job.get_work_mode_display() if job else "",
            location=location,
            recruiter_name=recruiter.full_name if recruiter else "Recruiting Team",
            recruiter_designation=recruiter.designation if recruiter else "Recruiter",
            recruiter_avatar=media_url(recruiter.profile_image)
            if recruiter and recruiter.profile_image
            else None,
            recruiter_email=recruiter.official_email
            if recruiter and recruiter.official_email
            else "",
            panel=panel,
            timeline=timeline,
            recruiter_updates=updates,
            feedback=feedback,
            calendar_url=self._google_calendar_url(app, meta, scheduled_at),
            countdown_seconds=self._countdown_seconds(app, scheduled_at),
        )

    def _interview_meta(self, app: JobApplication) -> tuple[dict, datetime]:
        interview = self._interviews.latest_for_application(app)
        if interview:
            meta = interview.to_metadata()
            scheduled_at = interview.scheduled_at
            return meta, scheduled_at

        meta = {}
        for event in app.timeline.all():
            if (
                event.to_status == JobApplicationStatus.INTERVIEW_SCHEDULED
                and event.metadata
            ):
                meta = dict(event.metadata)
                break
        scheduled_raw = meta.get("scheduled_at") or app.status_changed_at
        if isinstance(scheduled_raw, str):
            scheduled_at = datetime.fromisoformat(scheduled_raw.replace("Z", "+00:00"))
        else:
            scheduled_at = scheduled_raw
        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at)
        return meta, scheduled_at

    @staticmethod
    def _resolve_status_key(app: JobApplication, meta: dict) -> str:
        if meta.get("cancelled"):
            return "cancelled"
        if meta.get("rescheduled"):
            return "rescheduled"
        if meta.get("confirmed") or meta.get("candidate_confirmed"):
            return "confirmed"
        if app.status == JobApplicationStatus.HIRED:
            return "hired"
        if app.status == JobApplicationStatus.REJECTED:
            return "rejected"
        if app.status in (
            JobApplicationStatus.OFFER_RELEASED,
            JobApplicationStatus.OFFER_ACCEPTED,
        ):
            return "offer"
        if app.status == JobApplicationStatus.INTERVIEW_COMPLETED:
            return "completed"
        if app.status == JobApplicationStatus.SHORTLISTED:
            return "shortlisted"
        if app.status == JobApplicationStatus.INTERVIEW_SCHEDULED:
            return "scheduled"
        return "waiting"

    @staticmethod
    def _can_join(app: JobApplication, scheduled_at: datetime, meta: dict) -> bool:
        if app.status != JobApplicationStatus.INTERVIEW_SCHEDULED:
            return False
        if not (meta.get("meet_url") or meta.get("meeting_link")):
            return False
        now = timezone.now()
        window_start = scheduled_at - timedelta(minutes=JOIN_WINDOW_MINUTES)
        window_end = scheduled_at + timedelta(hours=2)
        return window_start <= now <= window_end

    @staticmethod
    def _countdown_seconds(app: JobApplication, scheduled_at: datetime) -> int | None:
        if app.status != JobApplicationStatus.INTERVIEW_SCHEDULED:
            return None
        delta = scheduled_at - timezone.now()
        if delta.total_seconds() <= 0:
            return None
        return int(delta.total_seconds())

    @staticmethod
    def _parse_panel(panel_raw, meta: dict) -> list[PanelMember]:
        members: list[PanelMember] = []
        if isinstance(panel_raw, list):
            for item in panel_raw:
                if isinstance(item, dict):
                    members.append(
                        PanelMember(
                            name=item.get("name", "Interviewer"),
                            designation=item.get(
                                "designation", item.get("role", "Panelist")
                            ),
                            department=item.get("department", ""),
                        )
                    )
                elif isinstance(item, str):
                    members.append(
                        PanelMember(name=item, designation="Panelist", department="")
                    )
        elif isinstance(panel_raw, str) and panel_raw:
            for name in panel_raw.split(","):
                members.append(
                    PanelMember(
                        name=name.strip(), designation="Panelist", department=""
                    )
                )
        if not members and meta.get("panel_lead"):
            members.append(
                PanelMember(
                    name=meta["panel_lead"],
                    designation=meta.get("panel_lead_designation", "Interviewer"),
                    department=meta.get("panel_department", ""),
                )
            )
        return members

    def _interview_timeline(self, app: JobApplication) -> list[InterviewTimelineEntry]:
        entries: list[InterviewTimelineEntry] = []
        recruiter = app.job_posting.posted_by if app.job_posting_id else None
        recruiter_name = recruiter.full_name if recruiter else "Recruiting Team"
        for event in self._timeline.for_application(app).order_by("occurred_at"):
            ui = self._portal._timeline_ui(event)
            when = timezone.localtime(event.occurred_at)
            entries.append(
                InterviewTimelineEntry(
                    title=ui["title"],
                    description=event.notes or ui["description"],
                    actor_name=recruiter_name,
                    occurred_date=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                    icon=ui["icon"],
                    tone=ui["tone"],
                )
            )
        return entries

    @staticmethod
    def _recruiter_updates(app: JobApplication) -> list[RecruiterUpdate]:
        updates: list[RecruiterUpdate] = []
        recruiter = app.job_posting.posted_by if app.job_posting_id else None
        name = recruiter.full_name if recruiter else "Recruiting Team"
        for event in app.timeline.filter(
            event_type=TimelineEventType.RECRUITER_COMMENT
        ).order_by("-occurred_at")[:10]:
            when = timezone.localtime(event.occurred_at)
            updates.append(
                RecruiterUpdate(
                    message=event.notes,
                    recruiter_name=name,
                    occurred_date=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                )
            )
        return updates

    @staticmethod
    def _feedback(meta: dict) -> InterviewFeedback:
        fb = meta.get("feedback") or {}
        shared = bool(meta.get("feedback_shared") or fb)
        if not shared:
            return InterviewFeedback(
                visible=False,
                technical=None,
                communication=None,
                problem_solving=None,
                overall=None,
                comments=None,
                confidential_message="Feedback will be shared after the recruitment process.",
            )
        return InterviewFeedback(
            visible=True,
            technical=fb.get("technical"),
            communication=fb.get("communication"),
            problem_solving=fb.get("problem_solving"),
            overall=fb.get("overall"),
            comments=fb.get("comments"),
            confidential_message="",
        )

    @staticmethod
    def _google_calendar_url(
        app: JobApplication, meta: dict, scheduled_at: datetime
    ) -> str:
        start = scheduled_at.strftime("%Y%m%dT%H%M%S")
        end = (
            scheduled_at + timedelta(minutes=int(meta.get("duration_minutes") or 45))
        ).strftime("%Y%m%dT%H%M%S")
        title = quote(
            f"Interview: {app.job_title_snapshot} at {app.company_name_snapshot}"
        )
        details = quote(meta.get("instructions", ""))
        location = quote(
            meta.get("meet_url") or meta.get("meeting_link") or meta.get("location", "")
        )
        return (
            f"https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={title}&dates={start}/{end}&details={details}&location={location}"
        )

    @staticmethod
    def _apply_filters(
        cards: list[InterviewListCard], *, status_filter: str, when: str
    ) -> list[InterviewListCard]:
        result = cards
        if status_filter == "upcoming":
            result = [c for c in result if c.is_upcoming]
        elif status_filter == "completed":
            result = [
                c for c in result if c.status_key in {"completed", "offer", "hired"}
            ]
        elif status_filter == "cancelled":
            result = [c for c in result if c.status_key == "cancelled"]
        elif status_filter == "today":
            result = [c for c in result if c.is_today]
        elif status_filter == "week":
            cutoff = timezone.localtime() + timedelta(days=7)
            result = [
                c
                for c in result
                if c.is_upcoming
                and datetime.fromisoformat(c.scheduled_at_iso).date() <= cutoff.date()
            ]
        if when and not status_filter:
            pass
        return result

    @staticmethod
    def _summary_cards(cards: list[InterviewListCard]) -> list[InterviewSummaryCard]:
        now = timezone.localtime()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        upcoming = sum(1 for c in cards if c.is_upcoming)
        today = sum(1 for c in cards if c.is_today and c.is_upcoming)
        completed = sum(
            1 for c in cards if c.status_key in {"completed", "offer", "hired"}
        )
        cancelled = sum(1 for c in cards if c.status_key == "cancelled")
        rescheduled = sum(1 for c in cards if c.status_key == "rescheduled")
        offers = sum(1 for c in cards if c.status_key == "offer")
        this_month = sum(
            1
            for c in cards
            if datetime.fromisoformat(c.scheduled_at_iso).replace(tzinfo=now.tzinfo)
            >= month_start
        )
        return [
            InterviewSummaryCard(
                "upcoming",
                "Upcoming Interviews",
                upcoming,
                "bi-calendar-event-fill",
                "interview",
            ),
            InterviewSummaryCard(
                "today", "Today's Interviews", today, "bi-alarm-fill", "info"
            ),
            InterviewSummaryCard(
                "completed",
                "Completed Interviews",
                completed,
                "bi-check2-all",
                "success",
            ),
            InterviewSummaryCard(
                "cancelled",
                "Cancelled Interviews",
                cancelled,
                "bi-x-circle-fill",
                "danger",
            ),
            InterviewSummaryCard(
                "rescheduled",
                "Rescheduled Interviews",
                rescheduled,
                "bi-arrow-repeat",
                "review",
            ),
            InterviewSummaryCard(
                "offers_pending", "Offers Pending", offers, "bi-envelope-open", "offer"
            ),
            InterviewSummaryCard(
                "offers_received",
                "Offers Received",
                offers,
                "bi-envelope-open-heart-fill",
                "offer",
            ),
            InterviewSummaryCard(
                "this_month",
                "Interviews This Month",
                this_month,
                "bi-calendar3",
                "primary",
            ),
        ]

    @staticmethod
    def _analytics(cards: list[InterviewListCard]) -> dict:
        total = len(cards) or 1
        completed = sum(
            1
            for c in cards
            if c.status_key in {"completed", "offer", "hired", "rejected"}
        )
        upcoming = sum(1 for c in cards if c.is_upcoming)
        cancelled = sum(1 for c in cards if c.status_key == "cancelled")
        rescheduled = sum(1 for c in cards if c.status_key == "rescheduled")
        offers = sum(1 for c in cards if c.status_key == "offer")
        success = round((offers / completed) * 100) if completed else 0
        return {
            "total": len(cards),
            "completed": completed,
            "upcoming": upcoming,
            "cancelled": cancelled,
            "rescheduled": rescheduled,
            "offers_received": offers,
            "offer_acceptance_rate": success,
            "interview_success_rate": round((offers / total) * 100, 1),
        }
