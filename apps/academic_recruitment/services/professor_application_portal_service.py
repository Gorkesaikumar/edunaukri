"""Professor application list and detail portal service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.formats import date_format

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_portal_helpers import (
    application_filters_query,
    faculty_status_ui,
    institution_profile_url,
    media_url,
)
from apps.applications.constants.faculty_enums import (
    FACULTY_TERMINAL_STATUSES,
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)
from apps.applications.models import FacultyApplication
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.selectors.timeline_selector import (
    FacultyApplicationTimelineSelector,
)
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.services.jobseeker_portal_helpers import format_salary_lpa
from apps.applications.services.joining_status_resolver import JoiningStatusResolver

OFFER_ACTION_STATUSES = frozenset({FacultyApplicationStatus.OFFER_RELEASED})

OFFER_VISIBLE_STATUSES = frozenset({
    FacultyApplicationStatus.OFFER_RELEASED,
    FacultyApplicationStatus.OFFER_ACCEPTED,
    FacultyApplicationStatus.OFFER_DECLINED,
    FacultyApplicationStatus.SELECTED,
    FacultyApplicationStatus.JOINING_IN_PROGRESS,
    FacultyApplicationStatus.JOINED,
})


@dataclass
class ApplicationAnalyticsCard:
    key: str
    label: str
    value: int
    icon: str
    tone: str


@dataclass
class ApplicationListCard:
    id: str
    job_title: str
    institution_name: str
    location: str
    logo_url: str | None
    status_label: str
    status_class: str
    applied_date: str
    last_updated: str
    detail_url: str
    job_url: str
    is_active: bool


@dataclass
class OfferDetails:
    salary_display: str
    designation: str
    joining_date: str
    expiry_label: str | None
    letter_url: str | None


@dataclass
class TimelineEntry:
    title: str
    description: str
    occurred_at: str


@dataclass
class InterviewPanelContext:
    date_label: str
    time_label: str
    interview_type: str
    location_label: str | None
    meet_url: str | None
    can_join: bool


@dataclass
class ApplicationDetailContext:
    application_id: str
    job_title: str
    institution_name: str
    location: str
    department: str
    status_label: str
    status_class: str
    applied_date: str
    last_updated: str
    cover_letter: str
    detail_url: str
    job_url: str
    cv_snapshot: dict = field(default_factory=dict)
    qualification_snapshot: list = field(default_factory=list)
    specialization_snapshot: dict = field(default_factory=dict)
    experience_snapshot: dict = field(default_factory=dict)
    certificates_snapshot: list = field(default_factory=list)
    expected_salary: str | None = None
    current_institution: str = ""
    current_designation: str = ""
    research_publications_count: int = 0
    source: str = ""
    institution_profile_url: str | None = None
    interview: InterviewPanelContext | None = None
    offer: OfferDetails | None = None
    can_accept_offer: bool = False
    can_decline_offer: bool = False
    offer_api_url: str = ""
    timeline: list[TimelineEntry] = field(default_factory=list)


@dataclass
class ApplicationsPageContext:
    applications: list[ApplicationListCard]
    analytics: list[ApplicationAnalyticsCard]
    filters: dict
    page: int
    total_pages: int
    total_count: int
    pagination_prev_query: str = ""
    pagination_next_query: str = ""


class ProfessorApplicationPortalService(BaseService):
    PAGE_SIZE = 10

    def list_applications(
        self,
        profile: ProfessorProfile,
        *,
        page: int = 1,
        status: str = "",
        q: str = "",
        active_only: bool = False,
        interview_only: bool = False,
        offer_only: bool = False,
        rejected_only: bool = False,
    ) -> ApplicationsPageContext:
        qs = (
            FacultyApplicationSelector()
            .for_professor(profile)
            .select_related(
                "vacancy", "college", "vacancy__college", "vacancy__college__logo_file"
            )
        )

        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(vacancy_title_snapshot__icontains=q)
                | Q(college_name_snapshot__icontains=q)
                | Q(department__icontains=q)
            )
        if active_only:
            qs = qs.exclude(status__in=FACULTY_TERMINAL_STATUSES)
        if interview_only:
            qs = qs.filter(
                status__in=[
                    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                    FacultyApplicationStatus.INTERVIEW_COMPLETED,
                ]
            )
        if offer_only:
            qs = qs.filter(
                status__in=[
                    FacultyApplicationStatus.OFFER_RELEASED,
                    FacultyApplicationStatus.OFFER_ACCEPTED,
                    FacultyApplicationStatus.OFFER_DECLINED,
                ]
            )
        if rejected_only:
            qs = qs.filter(status=FacultyApplicationStatus.REJECTED)

        paginator = Paginator(qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)
        user = profile.user
        cards = [self._map_card(app, user) for app in page_obj.object_list]

        stats = FacultyApplicationStatisticsService().professor_dashboard(profile)
        by_status = stats.get("applications_by_status", {})
        analytics = [
            ApplicationAnalyticsCard(
                "total",
                "Total Applied",
                stats["total_applications"],
                "bi-send",
                "primary",
            ),
            ApplicationAnalyticsCard(
                "active", "Active", stats["active_applications"], "bi-lightning", "info"
            ),
            ApplicationAnalyticsCard(
                "interview",
                "Interviews",
                by_status.get(FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0)
                + by_status.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0),
                "bi-calendar-event",
                "info",
            ),
            ApplicationAnalyticsCard(
                "offer",
                "Offers",
                by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0),
                "bi-envelope-check",
                "success",
            ),
        ]

        filters = {
            "status": status,
            "q": q,
            "active_only": active_only,
            "interview_only": interview_only,
            "offer_only": offer_only,
            "rejected_only": rejected_only,
        }

        return ApplicationsPageContext(
            applications=cards,
            analytics=analytics,
            filters=filters,
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
            pagination_prev_query=(
                application_filters_query(page_obj.number - 1, filters)
                if page_obj.has_previous()
                else ""
            ),
            pagination_next_query=(
                application_filters_query(page_obj.number + 1, filters)
                if page_obj.has_next()
                else ""
            ),
        )

    def get_detail(
        self, profile: ProfessorProfile, application_id
    ) -> ApplicationDetailContext | None:
        application = (
            FacultyApplication.objects.filter(
                pk=application_id,
                professor=profile,
                is_deleted=False,
            )
            .select_related("vacancy", "college", "vacancy__college")
            .first()
        )
        if application is None:
            return None

        user = profile.user
        label, css = faculty_status_ui(application.status)
        location = self._location(application)
        timeline = []
        for event in FacultyApplicationTimelineSelector().for_application(application)[
            :12
        ]:
            status_label = ""
            if event.to_status:
                try:
                    status_label = FacultyApplicationStatus(event.to_status).label
                except ValueError:
                    status_label = event.to_status.replace("_", " ").title()
            timeline.append(
                TimelineEntry(
                    title=status_label or event.get_event_type_display(),
                    description=event.notes or "",
                    occurred_at=date_format(
                        timezone.localtime(event.occurred_at), "M j, Y g:i A"
                    ),
                )
            )

        college = application.college or (
            application.vacancy.college if application.vacancy_id else None
        )
        interview_panel = self._interview_panel(application)
        offer = self._extract_offer(application, timeline)

        return ApplicationDetailContext(
            application_id=str(application.pk),
            job_title=application.vacancy_title_snapshot,
            institution_name=application.college_name_snapshot or "Institution",
            location=location,
            department=application.department
            or (application.vacancy.department if application.vacancy_id else ""),
            status_label=label,
            status_class=css,
            applied_date=date_format(
                timezone.localtime(application.applied_at), "M j, Y"
            ),
            last_updated=date_format(
                timezone.localtime(application.status_changed_at), "M j, Y"
            ),
            cover_letter=application.cover_letter,
            detail_url=PortalURLService.professor(
                user, "professor_application_detail", application_id=application.pk
            ),
            job_url=PortalURLService.professor(
                user, "professor_vacancy_detail", vacancy_id=application.vacancy_id
            ),
            cv_snapshot=application.cv_snapshot or {},
            qualification_snapshot=application.qualification_snapshot or [],
            specialization_snapshot=application.specialization_snapshot or {},
            experience_snapshot=application.experience_snapshot or {},
            certificates_snapshot=application.certificates_snapshot or [],
            expected_salary=str(application.expected_salary) if application.expected_salary else None,
            current_institution=application.current_institution,
            current_designation=application.current_designation,
            research_publications_count=application.research_publications_count,
            source=application.get_source_display() if application.source else "",
            institution_profile_url=institution_profile_url(college),
            interview=interview_panel,
            offer=offer,
            can_accept_offer=self.can_respond_to_offer(application),
            can_decline_offer=self.can_respond_to_offer(application),
            offer_api_url=PortalURLService.professor(
                user, "professor_application_offer_api", application_id=application.pk
            ),
            timeline=timeline,
        )

    @staticmethod
    def can_respond_to_offer(application: FacultyApplication) -> bool:
        return application.status in OFFER_ACTION_STATUSES

    def _map_card(self, app: FacultyApplication, user) -> ApplicationListCard:
        label, css = faculty_status_ui(app.status)
        college = app.college or (app.vacancy.college if app.vacancy_id else None)
        logo = (
            media_url(college.logo_file)
            if college and getattr(college, "logo_file_id", None)
            else None
        )
        return ApplicationListCard(
            id=str(app.pk),
            job_title=app.vacancy_title_snapshot,
            institution_name=app.college_name_snapshot or "Institution",
            location=self._location(app),
            logo_url=logo,
            status_label=label,
            status_class=css,
            applied_date=date_format(timezone.localtime(app.applied_at), "M j, Y"),
            last_updated=date_format(
                timezone.localtime(app.status_changed_at), "M j, Y"
            ),
            detail_url=PortalURLService.professor(
                user, "professor_application_detail", application_id=app.pk
            ),
            job_url=PortalURLService.professor(
                user, "professor_vacancy_detail", vacancy_id=app.vacancy_id
            ),
            is_active=app.status not in FACULTY_TERMINAL_STATUSES,
        )

    @staticmethod
    def _extract_offer(
        application: FacultyApplication, timeline: list[TimelineEntry]
    ) -> OfferDetails | None:
        if application.status not in OFFER_VISIBLE_STATUSES:
            return None
        meta = {}
        for event in (
            FacultyApplicationTimelineSelector()
            .for_application(application)
            .order_by("-occurred_at")
        ):
            if event.event_type == FacultyTimelineEventType.OFFER and event.metadata:
                meta = event.metadata
                break
        vacancy = application.vacancy if application.vacancy_id else None
        salary = meta.get("offered_salary") or meta.get("salary")
        if salary is None and vacancy:
            salary = format_salary_lpa(
                vacancy.salary_min, vacancy.salary_max, vacancy.salary_currency or "INR"
            )
        elif salary is not None:
            salary = str(salary)
        expiry = meta.get("offer_expiry") or meta.get("expires_at")
        expiry_label = None
        if expiry:
            try:
                from datetime import datetime
                exp = timezone.localtime(
                    datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
                    if isinstance(expiry, str)
                    else expiry
                )
                expiry_label = exp.strftime("%b %d, %Y")
            except (TypeError, ValueError):
                expiry_label = str(expiry)

        # ── Centralized joining status (single source of truth) ──
        joining_label, joining_date_str = JoiningStatusResolver.resolve_faculty(
            application, offer_meta=meta
        )
        joining_display = JoiningStatusResolver.joining_display(joining_label, joining_date_str)

        return OfferDetails(
            salary_display=salary or "As discussed",
            designation=meta.get(
                "designation",
                vacancy.title if vacancy else application.vacancy_title_snapshot,
            ),
            joining_date=joining_display,
            expiry_label=expiry_label,
            letter_url=meta.get("offer_letter_url") or meta.get("letter_url"),
        )

    @staticmethod
    def _interview_panel(
        application: FacultyApplication,
    ) -> InterviewPanelContext | None:
        if application.status not in (
            FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            FacultyApplicationStatus.INTERVIEW_COMPLETED,
        ):
            return None
        from apps.academic_recruitment.services.professor_interview_portal_service import (
            ProfessorInterviewPortalService,
        )

        meta = ProfessorInterviewPortalService._interview_meta(application)
        dt = meta.get("datetime")
        now = timezone.now()
        meet_url = meta.get("meet_url")
        is_upcoming = (
            application.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED
            and dt
            and dt >= now
        )
        return InterviewPanelContext(
            date_label=date_format(dt, "M j, Y") if dt else "TBD",
            time_label=dt.strftime("%I:%M %p").lstrip("0") if dt else "",
            interview_type=meta.get("interview_type") or "Interview",
            location_label=meta.get("location"),
            meet_url=meet_url,
            can_join=bool(meet_url and is_upcoming),
        )

    @staticmethod
    def _location(app: FacultyApplication) -> str:
        vacancy = app.vacancy if app.vacancy_id else None
        if vacancy:
            parts = [p for p in [vacancy.city, vacancy.state] if p]
            if parts:
                return ", ".join(parts)
        return app.department or "Location not specified"
