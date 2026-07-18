"""Professor interview list portal service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_portal_helpers import (
    faculty_status_ui,
    institution_profile_url,
    interview_filters_query,
    media_url,
)
from apps.applications.constants.faculty_enums import (
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)
from apps.applications.models import FacultyApplication, FacultyApplicationTimelineEvent
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.selectors.timeline_selector import (
    FacultyApplicationTimelineSelector,
)
from apps.applications.services.faculty_application_history_service import (
    FacultyApplicationHistoryService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService

INTERVIEW_APP_STATUSES = (
    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
    FacultyApplicationStatus.INTERVIEW_COMPLETED,
    FacultyApplicationStatus.OFFER_RELEASED,
    FacultyApplicationStatus.OFFER_ACCEPTED,
    FacultyApplicationStatus.JOINED,
    FacultyApplicationStatus.REJECTED,
)

JOIN_WINDOW_MINUTES = 15

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
    "completed": (
        "Interview Completed",
        "jsd-int-badge--completed",
        "bi-check2-all",
        "This interview round is complete.",
    ),
    "offer": (
        "Offer Released",
        "jsd-int-badge--offer",
        "bi-envelope-open-heart",
        "Offer released after interview process.",
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
class InterviewListCard:
    application_id: str
    job_title: str
    institution_name: str
    logo_url: str | None
    status_label: str
    status_class: str
    date_label: str
    time_label: str
    month_label: str
    day_label: str
    interview_type: str
    meet_url: str | None
    location_label: str | None
    detail_url: str
    can_join: bool
    is_upcoming: bool


@dataclass
class InterviewsPageContext:
    interviews: list[InterviewListCard]
    summary: list[InterviewSummaryCard]
    filters: dict
    page: int
    total_pages: int
    total_count: int
    pagination_prev_query: str = ""
    pagination_next_query: str = ""


class ProfessorInterviewPortalService(BaseService):
    PAGE_SIZE = 10

    def list_interviews(
        self,
        profile: ProfessorProfile,
        *,
        page: int = 1,
        q: str = "",
        status_filter: str = "",
    ) -> InterviewsPageContext:
        qs = (
            FacultyApplicationSelector()
            .for_professor(profile)
            .filter(status__in=INTERVIEW_APP_STATUSES)
            .select_related(
                "vacancy", "college", "vacancy__college", "vacancy__college__logo_file"
            )
        )

        if q:
            qs = qs.filter(
                Q(vacancy_title_snapshot__icontains=q)
                | Q(college_name_snapshot__icontains=q)
            )

        if status_filter == "upcoming":
            qs = qs.filter(status=FacultyApplicationStatus.INTERVIEW_SCHEDULED)
        elif status_filter == "completed":
            qs = qs.filter(status=FacultyApplicationStatus.INTERVIEW_COMPLETED)
        elif status_filter == "offer":
            qs = qs.filter(
                status__in=[
                    FacultyApplicationStatus.OFFER_RELEASED,
                    FacultyApplicationStatus.OFFER_ACCEPTED,
                    FacultyApplicationStatus.JOINED,
                ]
            )

        paginator = Paginator(qs.order_by("-status_changed_at"), self.PAGE_SIZE)
        page_obj = paginator.get_page(page)
        cards = [self._map_card(app, profile.user) for app in page_obj.object_list]

        base = FacultyApplicationSelector().for_professor(profile)
        summary = [
            InterviewSummaryCard(
                "scheduled",
                "Scheduled",
                base.filter(
                    status=FacultyApplicationStatus.INTERVIEW_SCHEDULED
                ).count(),
                "bi-calendar-event",
                "info",
            ),
            InterviewSummaryCard(
                "completed",
                "Completed",
                base.filter(
                    status=FacultyApplicationStatus.INTERVIEW_COMPLETED
                ).count(),
                "bi-check2-circle",
                "success",
            ),
            InterviewSummaryCard(
                "offers",
                "Post-Interview Offers",
                base.filter(
                    status__in=[
                        FacultyApplicationStatus.OFFER_RELEASED,
                        FacultyApplicationStatus.OFFER_ACCEPTED,
                    ]
                ).count(),
                "bi-envelope-check",
                "primary",
            ),
        ]

        filters = {"q": q, "status": status_filter}

        return InterviewsPageContext(
            interviews=cards,
            summary=summary,
            filters=filters,
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
            pagination_prev_query=(
                interview_filters_query(page_obj.number - 1, filters)
                if page_obj.has_previous()
                else ""
            ),
            pagination_next_query=(
                interview_filters_query(page_obj.number + 1, filters)
                if page_obj.has_next()
                else ""
            ),
        )

    def _map_card(self, app: FacultyApplication, user) -> InterviewListCard:
        label, css = faculty_status_ui(app.status)
        meta = self._interview_meta(app)
        dt = meta["datetime"]
        college = app.college or (app.vacancy.college if app.vacancy_id else None)
        logo = (
            media_url(college.logo_file)
            if college and getattr(college, "logo_file_id", None)
            else None
        )
        meet_url = meta.get("meet_url")
        now = timezone.now()
        is_upcoming = (
            app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED
            and dt
            and dt >= now
        )

        return InterviewListCard(
            application_id=str(app.pk),
            job_title=app.vacancy_title_snapshot,
            institution_name=app.college_name_snapshot or "Institution",
            logo_url=logo,
            status_label=label,
            status_class=css,
            date_label=date_format(timezone.localtime(dt), "M j, Y") if dt else "TBD",
            time_label=dt.strftime("%I:%M %p").lstrip("0") if dt else "",
            month_label=dt.strftime("%b").upper() if dt else "",
            day_label=str(dt.day) if dt else "—",
            interview_type=meta.get("interview_type") or "Interview",
            meet_url=meet_url,
            location_label=meta.get("location"),
            detail_url=PortalURLService.professor(
                user, "professor_interview_detail", application_id=app.pk
            ),
            can_join=bool(meet_url and is_upcoming),
            is_upcoming=is_upcoming,
        )

    @staticmethod
    def _interview_meta(app: FacultyApplication) -> dict:
        event = (
            FacultyApplicationTimelineEvent.objects.filter(
                application=app,
                to_status=FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            )
            .order_by("-occurred_at")
            .first()
        )
        meta = (event.metadata if event else {}) or {}
        dt = timezone.localtime(app.status_changed_at)
        scheduled_raw = meta.get("scheduled_at") or meta.get("interview_at")
        if scheduled_raw:
            parsed = parse_datetime(str(scheduled_raw))
            if parsed:
                dt = (
                    timezone.localtime(parsed)
                    if timezone.is_aware(parsed)
                    else timezone.make_aware(parsed)
                )
        return {
            "datetime": dt,
            "meet_url": meta.get("meeting_link")
            or meta.get("meet_url")
            or meta.get("join_url"),
            "location": meta.get("location") or meta.get("venue"),
            "interview_type": meta.get("interview_type")
            or meta.get("mode")
            or "Interview",
            "instructions": meta.get("instructions") or "",
            "panel_lead": meta.get("panel_lead") or "",
            "duration_minutes": meta.get("duration_minutes") or 45,
            "confirmed": bool(meta.get("candidate_confirmed")),
        }


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
class InterviewDetailContext:
    application_id: str
    interview_id: str
    job_title: str
    company_name: str
    company_verified: bool
    department: str
    location: str
    salary_display: str
    employment_type: str
    work_mode: str
    company_profile_url: str | None
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
    instructions: str
    can_join: bool
    can_confirm: bool
    can_reschedule: bool
    countdown_seconds: int | None
    calendar_url: str
    timeline: list[InterviewTimelineEntry] = field(default_factory=list)
    panel_members: list[dict] = field(default_factory=list)
    application_detail_url: str = ""
    print_url: str = ""


def _professor_interview_detail_impl(
    self: ProfessorInterviewPortalService, profile, application_id
):
    app = (
        FacultyApplicationSelector()
        .for_professor(profile)
        .filter(pk=application_id)
        .select_related(
            "vacancy", "college", "vacancy__college", "vacancy__college__logo_file"
        )
        .prefetch_related("timeline")
        .first()
    )
    if not app or app.status not in INTERVIEW_APP_STATUSES:
        return None
    return self._map_detail(app, profile.user)


ProfessorInterviewPortalService._get_detail = _professor_interview_detail_impl


def _map_detail_impl(
    self: ProfessorInterviewPortalService, app: FacultyApplication, user
) -> InterviewDetailContext:
    pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
    meta = self._interview_meta(app)
    dt = meta["datetime"]
    status_key = self._status_key(app, meta)
    label, badge, icon, desc = INTERVIEW_STATUS_UI.get(
        status_key,
        (
            "Interview",
            "jsd-int-badge--scheduled",
            "bi-calendar-event",
            "Interview details",
        ),
    )
    vacancy = app.vacancy if app.vacancy_id else None
    college = app.college or (vacancy.college if vacancy else None)
    location_parts = []
    if vacancy:
        location_parts = [p for p in [vacancy.city, vacancy.state] if p]
    panel_raw = meta.get("panel") or meta.get("panel_members") or []
    panel_members = []
    if isinstance(panel_raw, list):
        for item in panel_raw:
            if isinstance(item, dict):
                panel_members.append(item)
            elif isinstance(item, str):
                panel_members.append({"name": item, "designation": "Panelist"})
    elif meta.get("panel_lead"):
        panel_members.append({"name": meta["panel_lead"], "designation": "Interviewer"})

    scheduled_iso = dt.isoformat() if dt else ""
    countdown = None
    if app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED and dt:
        delta = dt - timezone.now()
        if delta.total_seconds() > 0:
            countdown = int(delta.total_seconds())

    meet_url = meta.get("meet_url")
    can_join = self._can_join(app, dt, meta) if dt else False
    can_confirm = (
        app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED
        and not meta.get("confirmed")
    )
    can_reschedule = app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED

    return InterviewDetailContext(
        application_id=str(app.pk),
        interview_id=str(app.pk),
        job_title=app.vacancy_title_snapshot,
        company_name=app.college_name_snapshot or "Institution",
        company_verified=bool(college and getattr(college, "is_verified", False)),
        department=(vacancy.department if vacancy else app.department) or "—",
        location=", ".join(location_parts)
        if location_parts
        else (meta.get("location") or "—"),
        salary_display=getattr(vacancy, "salary_display", None)
        or "As per institution policy",
        employment_type=getattr(vacancy, "employment_type", None) or "Full-time",
        work_mode=getattr(vacancy, "work_mode", None)
        or meta.get("interview_type")
        or "On-campus",
        company_profile_url=institution_profile_url(college) if college else None,
        status_key=status_key,
        status_label=label,
        status_badge=badge,
        status_icon=icon,
        status_description=desc,
        round_label=meta.get("round") or "Interview Round",
        interview_type=meta.get("interview_type") or "Interview",
        mode=meta.get("interview_type") or "In-person / Online",
        date_label=date_format(dt, "M j, Y") if dt else "TBD",
        time_label=dt.strftime("%I:%M %p").lstrip("0") if dt else "",
        timezone_label=str(timezone.get_current_timezone()),
        duration_label=f"{meta.get('duration_minutes', 45)} minutes",
        scheduled_at_iso=scheduled_iso,
        meet_url=meet_url,
        instructions=meta.get("instructions") or "",
        can_join=can_join,
        can_confirm=can_confirm,
        can_reschedule=can_reschedule,
        countdown_seconds=countdown,
        calendar_url=self._google_calendar_url(app, meta, dt) if dt else "",
        timeline=self._interview_timeline(app),
        panel_members=panel_members,
        application_detail_url=pu(
            "professor_application_detail", application_id=app.pk
        ),
        print_url=pu("professor_interview_print", application_id=app.pk),
    )


ProfessorInterviewPortalService._map_detail = _map_detail_impl


def _status_key_impl(
    self: ProfessorInterviewPortalService, app: FacultyApplication, meta: dict
) -> str:
    if meta.get("confirmed"):
        return "confirmed"
    if app.status == FacultyApplicationStatus.INTERVIEW_COMPLETED:
        return "completed"
    if app.status in (
        FacultyApplicationStatus.OFFER_RELEASED,
        FacultyApplicationStatus.OFFER_ACCEPTED,
    ):
        return "offer"
    if app.status == FacultyApplicationStatus.REJECTED:
        return "rejected"
    return "scheduled"


ProfessorInterviewPortalService._status_key = _status_key_impl


def _can_join_impl(
    self: ProfessorInterviewPortalService,
    app: FacultyApplication,
    scheduled_at,
    meta: dict,
) -> bool:
    if app.status != FacultyApplicationStatus.INTERVIEW_SCHEDULED:
        return False
    if not meta.get("meet_url"):
        return False
    now = timezone.now()
    window_start = scheduled_at - timedelta(minutes=JOIN_WINDOW_MINUTES)
    window_end = scheduled_at + timedelta(hours=2)
    return window_start <= now <= window_end


ProfessorInterviewPortalService._can_join = _can_join_impl


def _google_calendar_url(app: FacultyApplication, meta: dict, scheduled_at) -> str:
    start = scheduled_at.strftime("%Y%m%dT%H%M%S")
    end = (
        scheduled_at + timedelta(minutes=int(meta.get("duration_minutes") or 45))
    ).strftime("%Y%m%dT%H%M%S")
    title = quote(
        f"Faculty Interview: {app.vacancy_title_snapshot} at {app.college_name_snapshot}"
    )
    details = quote(meta.get("instructions", ""))
    location = quote(meta.get("meet_url") or meta.get("location") or "")
    return (
        f"https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={title}&dates={start}/{end}&details={details}&location={location}"
    )


ProfessorInterviewPortalService._google_calendar_url = staticmethod(
    _google_calendar_url
)


def _interview_timeline_impl(
    self: ProfessorInterviewPortalService, app: FacultyApplication
) -> list[InterviewTimelineEntry]:
    entries: list[InterviewTimelineEntry] = []
    for event in (
        FacultyApplicationTimelineSelector()
        .for_application(app)
        .order_by("occurred_at")
    ):
        when = timezone.localtime(event.occurred_at)
        title = "Status updated"
        desc = event.notes or ""
        icon = "bi-arrow-repeat"
        tone = "info"
        if event.to_status == FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            title = "Interview scheduled"
            icon = "bi-calendar-event"
        elif event.event_type == FacultyTimelineEventType.PROFESSOR_ACTION:
            title = "Your update"
            icon = "bi-person-check"
        entries.append(
            InterviewTimelineEntry(
                title=title,
                description=desc,
                actor_name="Institution Recruiter",
                occurred_date=when.strftime("%b %d, %Y"),
                occurred_time=when.strftime("%I:%M %p"),
                icon=icon,
                tone=tone,
            )
        )
    return entries


ProfessorInterviewPortalService._interview_timeline = _interview_timeline_impl


def _confirm_attendance_impl(
    self: ProfessorInterviewPortalService, profile, application_id, *, actor
) -> None:
    app = (
        FacultyApplicationSelector()
        .for_professor(profile)
        .filter(pk=application_id)
        .first()
    )
    if not app:
        raise ValueError("Interview not found.")
    if app.status != FacultyApplicationStatus.INTERVIEW_SCHEDULED:
        raise ValueError("Only scheduled interviews can be confirmed.")
    FacultyApplicationHistoryService().record_comment(
        app,
        notes="Candidate confirmed interview attendance.",
        event_type=FacultyTimelineEventType.PROFESSOR_ACTION,
        actor_id=getattr(actor, "pk", None),
    )


ProfessorInterviewPortalService._confirm_attendance = _confirm_attendance_impl


def _request_reschedule_impl(
    self: ProfessorInterviewPortalService,
    profile,
    application_id,
    *,
    actor,
    reason: str = "",
) -> None:
    app = (
        FacultyApplicationSelector()
        .for_professor(profile)
        .filter(pk=application_id)
        .first()
    )
    if not app:
        raise ValueError("Interview not found.")
    if app.status != FacultyApplicationStatus.INTERVIEW_SCHEDULED:
        raise ValueError("Reschedule is not available for this interview.")
    note = reason.strip() or "Candidate requested a reschedule."
    FacultyApplicationHistoryService().record_comment(
        app,
        notes=f"Reschedule requested: {note}",
        event_type=FacultyTimelineEventType.PROFESSOR_ACTION,
        actor_id=getattr(actor, "pk", None),
    )


ProfessorInterviewPortalService._request_reschedule = _request_reschedule_impl

ProfessorInterviewPortalService.get_detail = lambda self, profile, application_id: (
    self._get_detail(profile, application_id)
)
ProfessorInterviewPortalService.confirm_attendance = (
    lambda self, profile, application_id, *, actor: self._confirm_attendance(
        profile, application_id, actor=actor
    )
)
ProfessorInterviewPortalService.request_reschedule = (
    lambda self, profile, application_id, *, actor, reason="": self._request_reschedule(
        profile, application_id, actor=actor, reason=reason
    )
)
