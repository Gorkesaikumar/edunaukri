"""Institution interview management for faculty applications."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format

from apps.applications.constants.faculty_enums import (
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)
from apps.applications.models import FacultyApplication, FacultyApplicationTimelineEvent
from apps.applications.repositories.application_repository import (
    FacultyApplicationTimelineRepository,
)
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService

INTERVIEW_TRACK_STATUSES = (
    FacultyApplicationStatus.SHORTLISTED,
    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
    FacultyApplicationStatus.DEPARTMENT_REVIEW,
    FacultyApplicationStatus.PRINCIPAL_REVIEW,
    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
    FacultyApplicationStatus.INTERVIEW_COMPLETED,
    FacultyApplicationStatus.SELECTED,
    FacultyApplicationStatus.JOINING_IN_PROGRESS,
    FacultyApplicationStatus.OFFER_RELEASED,
    FacultyApplicationStatus.OFFER_ACCEPTED,
    FacultyApplicationStatus.JOINED,
    FacultyApplicationStatus.REJECTED,
)

SCHEDULE_ELIGIBLE_STATUSES = (
    FacultyApplicationStatus.SHORTLISTED,
    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
    FacultyApplicationStatus.DEPARTMENT_REVIEW,
    FacultyApplicationStatus.PRINCIPAL_REVIEW,
    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
)
INTERVIEW_CHANNELS = {
    "walk_in": "Walk-in",
    "video": "Video Interview",
    "phone": "Phone Interview",
    "google_meet": "Google Meet",
    "zoom": "Zoom",
    "microsoft_teams": "Microsoft Teams",
}


@dataclass
class CollegeInterviewPageContext:
    interviews: list[dict]
    pending_candidates: list[dict]
    calendar_events: list[dict]
    summary: list[dict]
    filters: dict
    page: int
    total_pages: int
    total_count: int
    api_urls: dict


class CollegeInterviewPortalService(BaseService):
    PAGE_SIZE = 12

    def build(
        self,
        user,
        *,
        page: int = 1,
        q: str = "",
        status: str = "",
    ) -> CollegeInterviewPageContext:
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .filter(status__in=INTERVIEW_TRACK_STATUSES)
            .select_related(
                "vacancy", "vacancy__college", "professor", "professor__profile_photo"
            )
        )

        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(vacancy_title_snapshot__icontains=q)
                | Q(college_name_snapshot__icontains=q)
            )

        if status == "pending":
            qs = qs.filter(
                status__in=[
                    FacultyApplicationStatus.SHORTLISTED,
                    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                    FacultyApplicationStatus.DEPARTMENT_REVIEW,
                    FacultyApplicationStatus.PRINCIPAL_REVIEW,
                    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                ]
            )
        elif status == "scheduled":
            qs = qs.filter(status=FacultyApplicationStatus.INTERVIEW_SCHEDULED)
        elif status == "completed":
            qs = qs.filter(status=FacultyApplicationStatus.INTERVIEW_COMPLETED)
        elif status == "offer":
            qs = qs.filter(
                status__in=(
                    FacultyApplicationStatus.SELECTED,
                    FacultyApplicationStatus.JOINING_IN_PROGRESS,
                    FacultyApplicationStatus.OFFER_RELEASED,
                    FacultyApplicationStatus.OFFER_ACCEPTED,
                    FacultyApplicationStatus.JOINED,
                )
            )

        paginator = Paginator(qs.order_by("-status_changed_at"), self.PAGE_SIZE)
        page_obj = paginator.get_page(page)
        interviews = [
            self._serialize_application(app, user) for app in page_obj.object_list
        ]
        base = FacultyApplicationSelector().for_college_user(user)
        pending_statuses = [
            FacultyApplicationStatus.SHORTLISTED,
            FacultyApplicationStatus.ACADEMIC_VERIFICATION,
            FacultyApplicationStatus.DEPARTMENT_REVIEW,
            FacultyApplicationStatus.PRINCIPAL_REVIEW,
            FacultyApplicationStatus.MANAGEMENT_APPROVAL,
        ]
        summary = [
            {
                "key": "pending",
                "label": "Pending Schedule",
                "value": base.filter(
                    status__in=pending_statuses
                ).count(),
                "icon": "bi-hourglass-split",
                "tone": "secondary",
            },
            {
                "key": "scheduled",
                "label": "Scheduled",
                "value": base.filter(
                    status=FacultyApplicationStatus.INTERVIEW_SCHEDULED
                ).count(),
                "icon": "bi-calendar-event",
                "tone": "primary",
            },
            {
                "key": "completed",
                "label": "Completed",
                "value": base.filter(
                    status=FacultyApplicationStatus.INTERVIEW_COMPLETED
                ).count(),
                "icon": "bi-check2-circle",
                "tone": "success",
            },
            {
                "key": "offers",
                "label": "Post Interview Offers",
                "value": base.filter(
                    status__in=(
                        FacultyApplicationStatus.SELECTED,
                        FacultyApplicationStatus.JOINING_IN_PROGRESS,
                        FacultyApplicationStatus.OFFER_RELEASED,
                        FacultyApplicationStatus.OFFER_ACCEPTED,
                    )
                ).count(),
                "icon": "bi-envelope-check",
                "tone": "accent",
            },
        ]

        empty_uuid = "00000000-0000-0000-0000-000000000000"

        # Fetch SHORTLISTED candidates awaiting scheduling (separate from paginated list)
        pending_qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .filter(status=FacultyApplicationStatus.SHORTLISTED)
            .select_related(
                "vacancy", "professor", "professor__profile_photo", "professor__user"
            )
            .order_by("-status_changed_at")
        )
        if q:
            pending_qs = pending_qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(vacancy_title_snapshot__icontains=q)
            )
        pending_candidates = [
            self._serialize_pending(app, user) for app in pending_qs[:50]
        ]

        return CollegeInterviewPageContext(
            interviews=interviews,
            pending_candidates=pending_candidates,
            calendar_events=[
                {
                    "application_id": row["application_id"],
                    "candidate_name": row["candidate_name"],
                    "vacancy_title": row["vacancy_title"],
                    "scheduled_at": row["scheduled_at_iso"],
                    "date_label": row["date_label"],
                    "time_label": row["time_label"],
                    "status": row["status"],
                }
                for row in interviews
                if row.get("scheduled_at_iso")
            ],
            summary=summary,
            filters={"q": q, "status": status},
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
            api_urls={
                "schedule_template": pu(
                    "college_interview_schedule_api", application_id=empty_uuid
                ),
                "reschedule_template": pu(
                    "college_interview_reschedule_api", application_id=empty_uuid
                ),
                "cancel_template": pu(
                    "college_interview_cancel_api", application_id=empty_uuid
                ),
                "complete_template": pu(
                    "college_interview_complete_api", application_id=empty_uuid
                ),
                "select_template": pu(
                    "college_application_select_api", application_id=empty_uuid
                ),
                "reject_template": pu(
                    "college_application_status_api", application_id=empty_uuid
                ),
            },
        )

    @BaseService.atomic
    def schedule_interview(
        self,
        *,
        actor,
        application: FacultyApplication,
        scheduled_at_raw: str,
        interview_type: str,
        mode: str,
        meeting_platform: str,
        meet_url: str,
        location: str,
        interviewer_name: str,
        notes: str,
        duration_minutes: int,
    ) -> None:
        scheduled_at = self._parse_scheduled_at(scheduled_at_raw)
        if application.status not in SCHEDULE_ELIGIBLE_STATUSES:
            raise ValueError(
                "Interview cannot be scheduled for this application status."
            )

        if application.status != FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            FacultyApplicationService().update_status_for_actor(
                application,
                FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                notes.strip() or "Interview scheduled by institution.",
                actor=actor,
            )
            application.refresh_from_db()

        self._record_interview_event(
            application=application,
            actor=actor,
            notes=notes.strip() or "Interview schedule updated.",
            metadata={
                "scheduled_at": scheduled_at.isoformat(),
                "interview_type": (interview_type or "Interview").strip(),
                "mode": (mode or "Online").strip(),
                "meeting_platform": self._meeting_platform_label(meeting_platform),
                "meeting_link": meet_url.strip(),
                "location": location.strip(),
                "interviewer_name": interviewer_name.strip(),
                "duration_minutes": max(15, int(duration_minutes or 45)),
            },
        )

    @BaseService.atomic
    def mark_completed(self, *, actor, application: FacultyApplication) -> None:
        if application.status != FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            raise ValueError("Only scheduled interviews can be marked as completed.")
        FacultyApplicationService().update_status_for_actor(
            application,
            FacultyApplicationStatus.INTERVIEW_COMPLETED,
            "Interview marked as completed by institution.",
            actor=actor,
        )

    @BaseService.atomic
    def cancel_interview(
        self, *, actor, application: FacultyApplication, reason: str = ""
    ) -> None:
        if application.status != FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            raise ValueError("Only scheduled interviews can be cancelled.")
        note = (
            reason.strip()
            or "Interview cancelled by institution. Moved back to pending scheduling."
        )
        FacultyApplicationService().update_status_for_actor(
            application,
            FacultyApplicationStatus.SHORTLISTED,
            note,
            actor=actor,
        )

    def _serialize_application(self, app: FacultyApplication, user) -> dict:
        meta = self._latest_interview_meta(app)
        dt = meta.get("datetime")
        status_label = app.get_status_display()
        badge_class = "icd-badge--muted"
        if app.status == FacultyApplicationStatus.SHORTLISTED:
            status_label = "Pending Schedule"
            badge_class = "icd-badge--warning"
        elif app.status == FacultyApplicationStatus.MANAGEMENT_APPROVAL:
            status_label = "Pending Schedule"
            badge_class = "icd-badge--warning"
        elif app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            status_label = "Interview Scheduled"
            badge_class = "icd-badge--info"
        elif app.status == FacultyApplicationStatus.INTERVIEW_COMPLETED:
            status_label = "Interview Completed"
            badge_class = "icd-badge--success"
        elif app.status in (
            FacultyApplicationStatus.SELECTED,
            FacultyApplicationStatus.JOINING_IN_PROGRESS,
            FacultyApplicationStatus.OFFER_RELEASED,
            FacultyApplicationStatus.OFFER_ACCEPTED,
            FacultyApplicationStatus.JOINED,
        ):
            badge_class = "icd-badge--success"
        elif app.status == FacultyApplicationStatus.REJECTED:
            badge_class = "icd-badge--danger"

        return {
            "application_id": str(app.pk),
            "candidate_name": app.applicant_name_snapshot,
            "vacancy_title": app.vacancy_title_snapshot,
            "institution_name": app.college_name_snapshot or "Institution",
            "status": app.status,
            "status_label": status_label,
            "status_badge": badge_class,
            "date_label": date_format(timezone.localtime(dt), "M j, Y")
            if dt
            else "TBD",
            "time_label": dt.strftime("%I:%M %p").lstrip("0") if dt else "",
            "scheduled_at_iso": dt.isoformat() if dt else "",
            "interview_type": meta.get("interview_type") or "Interview",
            "mode": meta.get("mode") or "Online",
            "meeting_platform": meta.get("meeting_platform") or "",
            "meeting_link": meta.get("meeting_link") or "",
            "location": meta.get("location") or "",
            "interviewer_name": meta.get("interviewer_name") or "",
            "duration_minutes": meta.get("duration_minutes") or 45,
            "notes": meta.get("notes") or "",
            "application_url": PortalURLService.college(
                user, "college_application_detail", application_id=app.pk
            ),
            "can_schedule": app.status in SCHEDULE_ELIGIBLE_STATUSES,
            "can_reschedule": app.status
            == FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            "can_cancel": app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            "can_complete": app.status == FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            "can_select": app.status == FacultyApplicationStatus.INTERVIEW_COMPLETED,
            "can_reject": app.status in (FacultyApplicationStatus.INTERVIEW_SCHEDULED, FacultyApplicationStatus.INTERVIEW_COMPLETED),
        }

    @staticmethod
    def _parse_scheduled_at(value: str):
        parsed = parse_datetime((value or "").strip())
        if not parsed:
            raise ValueError("Invalid schedule datetime.")
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        if parsed <= timezone.now():
            raise ValueError("Interview time must be in the future.")
        return parsed

    @staticmethod
    def _latest_interview_meta(app: FacultyApplication) -> dict:
        event = (
            FacultyApplicationTimelineEvent.objects.filter(
                application=app,
                to_status=FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            )
            .order_by("-occurred_at")
            .first()
        )
        data = (event.metadata if event else {}) or {}
        dt = None
        raw = data.get("scheduled_at") or data.get("interview_at")
        if raw:
            parsed = parse_datetime(str(raw))
            if parsed:
                dt = (
                    timezone.localtime(parsed)
                    if timezone.is_aware(parsed)
                    else timezone.make_aware(parsed)
                )
        return {
            "datetime": dt,
            "interview_type": data.get("interview_type") or data.get("round"),
            "mode": data.get("mode") or data.get("interview_mode"),
            "meeting_platform": data.get("meeting_platform") or data.get("platform"),
            "meeting_link": data.get("meeting_link")
            or data.get("meet_url")
            or data.get("join_url"),
            "location": data.get("location") or data.get("venue"),
            "interviewer_name": data.get("interviewer_name") or data.get("interviewer"),
            "duration_minutes": data.get("duration_minutes"),
            "notes": event.notes if event else "",
        }

    @staticmethod
    def _meeting_platform_label(value: str) -> str:
        key = (value or "").strip().lower()
        if key in INTERVIEW_CHANNELS:
            return INTERVIEW_CHANNELS[key]
        return (value or "").strip()

    @staticmethod
    def _record_interview_event(
        *, application: FacultyApplication, actor, notes: str, metadata: dict
    ) -> None:
        FacultyApplicationTimelineRepository().create(
            application=application,
            event_type=FacultyTimelineEventType.STATUS_CHANGED,
            from_status=application.status,
            to_status=FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            actor_id=getattr(actor, "pk", None),
            actor_domain=DomainType.FACULTY,
            notes=notes,
            metadata=metadata,
            occurred_at=timezone.now(),
        )

    def _serialize_pending(self, app: FacultyApplication, user) -> dict:
        """Serialize a SHORTLISTED application for the Pending Schedule section."""
        from apps.it_recruitment.services.jobseeker_portal_helpers import (
            initials_from_name,
            media_url,
        )
        professor = app.professor
        profile_photo_url = media_url(getattr(professor, "profile_photo", None)) or ""
        name = app.applicant_name_snapshot or "Faculty Applicant"
        qualification_snapshot = app.qualification_snapshot or []
        top_qualification = (
            qualification_snapshot[0].get("qualification")
            if qualification_snapshot
            else ""
        ) or getattr(professor, "highest_qualification", "") or "Not specified"
        experience_years = (app.experience_snapshot or {}).get(
            "experience_years"
        ) or getattr(professor, "experience_years", None)
        exp_label = (
            f"{experience_years} yrs" if experience_years is not None else "Not specified"
        )
        shortlisted_label = (
            timezone.localtime(app.status_changed_at).strftime("%b %d, %Y")
            if app.status_changed_at
            else timezone.localtime(app.applied_at).strftime("%b %d, %Y")
        )
        schedule_url = PortalURLService.college(
            user, "college_interview_schedule_api", application_id=app.pk
        )
        profile_url = PortalURLService.college(
            user, "college_application_profile_api", application_id=app.pk
        )
        cv_available = bool(
            app.cv_file_id or getattr(professor, "cv_file_id", None)
        )
        return {
            "application_id": str(app.pk),
            "candidate_name": name,
            "candidate_initials": initials_from_name(name, "FA"),
            "candidate_photo_url": profile_photo_url,
            "vacancy_title": app.vacancy_title_snapshot or "Faculty Role",
            "department": app.department or "",
            "qualification_label": top_qualification,
            "experience_label": exp_label,
            "shortlisted_label": shortlisted_label,
            "cv_available": cv_available,
            "schedule_url": schedule_url,
            "profile_url": profile_url,
        }
