"""Institution application detail portal service."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone
from django.utils.formats import date_format

from apps.accounts.models.college_user import CollegeUser
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.selectors.timeline_selector import (
    FacultyApplicationTimelineSelector,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.workflow.faculty_engine import FacultyApplicationWorkflowEngine
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.academic_recruitment.services.college_portal_helpers import (
    institution_status_ui,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    initials_from_name,
    media_url,
)


@dataclass
class TimelineEntry:
    title: str
    description: str
    occurred_at: str


@dataclass
class CollegeApplicationDetailContext:
    application_id: str
    candidate_name: str
    candidate_initials: str
    candidate_email: str
    candidate_phone: str
    photo_url: str | None
    vacancy_title: str
    vacancy_id: str
    department: str
    location: str
    status: str
    status_label: str
    status_class: str
    applied_label: str
    updated_label: str
    cover_letter: str
    current_institution: str
    current_designation: str
    expected_salary: str
    research_publications_count: int
    specialization: str
    qualifications: list[dict]
    certificates: list[dict]
    college_notes: str
    internal_remarks: str
    rejection_reason: str
    is_terminal: bool
    next_statuses: list[dict]
    status_url: str
    notes_url: str
    cv_url: str | None
    has_cv: bool
    timeline: list[TimelineEntry] = field(default_factory=list)
    list_url: str = ""


class CollegeApplicationDetailPortalService(BaseService):
    STATUS_LABELS = {choice.value: choice.label for choice in FacultyApplicationStatus}

    def get_detail(
        self, user: CollegeUser, application_id
    ) -> CollegeApplicationDetailContext | None:
        application = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .filter(pk=application_id)
            .select_related(
                "vacancy",
                "vacancy__college",
                "professor",
                "professor__user",
                "professor__profile_photo",
                "professor__cv_file",
                "cv_file",
                "college",
            )
            .first()
        )
        if application is None:
            return None
        try:
            ApplicationAuthorizationService().ensure_can_view_faculty_application(
                application, user
            )
        except PermissionDeniedException:
            return None

        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        professor = application.professor
        status_label, status_class = institution_status_ui(application.status)
        next_statuses = sorted(
            FacultyApplicationWorkflowEngine.transitions.get(application.status, set()),
            key=lambda s: self.STATUS_LABELS.get(s, s),
        )
        timeline = []
        for event in FacultyApplicationTimelineSelector().for_application(application)[
            :15
        ]:
            title = ""
            if event.to_status:
                try:
                    title = FacultyApplicationStatus(event.to_status).label
                except ValueError:
                    title = event.to_status.replace("_", " ").title()
            if not title:
                title = event.get_event_type_display()
            timeline.append(
                TimelineEntry(
                    title=title,
                    description=event.notes or "",
                    occurred_at=date_format(
                        timezone.localtime(event.occurred_at), "M j, Y g:i A"
                    ),
                )
            )

        cv_stored = application.cv_file or (
            professor.cv_file if professor and professor.cv_file_id else None
        )
        expected = application.expected_salary or (
            professor.expected_salary if professor else None
        )
        expected_label = (
            format_salary_lpa(expected, expected, "INR") if expected else "—"
        )

        return CollegeApplicationDetailContext(
            application_id=str(application.pk),
            candidate_name=application.applicant_name_snapshot
            or (professor.full_name if professor else "Faculty Applicant"),
            candidate_initials=initials_from_name(
                application.applicant_name_snapshot or "", "FA"
            ),
            candidate_email=getattr(professor.user, "email", "") if professor else "",
            candidate_phone=professor.phone if professor else "",
            photo_url=media_url(professor.profile_photo)
            if professor and professor.profile_photo_id
            else None,
            vacancy_title=application.vacancy_title_snapshot,
            vacancy_id=str(application.vacancy_id),
            department=application.department
            or (application.vacancy.department if application.vacancy_id else ""),
            location=self._location(application),
            status=application.status,
            status_label=status_label,
            status_class=status_class,
            applied_label=date_format(
                timezone.localtime(application.applied_at), "M j, Y"
            ),
            updated_label=date_format(
                timezone.localtime(application.status_changed_at), "M j, Y"
            ),
            cover_letter=application.cover_letter or "",
            current_institution=application.current_institution
            or (professor.current_institution if professor else "")
            or "—",
            current_designation=application.current_designation
            or (professor.current_designation if professor else "")
            or "—",
            expected_salary=expected_label,
            research_publications_count=application.research_publications_count
            or (professor.publications_count if professor else 0),
            specialization=professor.specialization if professor else "",
            qualifications=list(application.qualification_snapshot or [])[:6],
            certificates=list(application.certificates_snapshot or [])[:6],
            college_notes=application.college_notes or "",
            internal_remarks=application.internal_remarks or "",
            rejection_reason=application.rejection_reason or "",
            is_terminal=FacultyApplicationWorkflowEngine.is_terminal(
                application.status
            ),
            next_statuses=[
                {
                    "value": s,
                    "label": self.STATUS_LABELS.get(s, s.replace("_", " ").title()),
                }
                for s in next_statuses
            ],
            status_url=pu(
                "college_application_status_api", application_id=application.pk
            ),
            notes_url=pu(
                "college_application_notes_api", application_id=application.pk
            ),
            cv_url=pu("college_application_cv_api", application_id=application.pk)
            if cv_stored
            else None,
            has_cv=bool(cv_stored),
            timeline=timeline,
            list_url=pu("college_applications"),
        )

    @staticmethod
    def _location(application: FacultyApplication) -> str:
        vacancy = application.vacancy if application.vacancy_id else None
        if vacancy:
            parts = [p for p in [vacancy.city, vacancy.state] if p]
            if parts:
                return ", ".join(parts)
        return application.department or "—"
