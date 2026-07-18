"""Aggregate dashboard data for the Faculty Job Seeker portal."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone
from django.utils.formats import date_format
from django.db.models import Count

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_portal_helpers import (
    FACULTY_STATUS_BADGES,
    faculty_status_ui,
    greeting_for_hour,
    media_url,
    INTERVIEW_STATUSES,
)
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.academic_recruitment.services.professor_vacancy_recommendation_service import (
    ProfessorVacancyRecommendationService,
)
from apps.accounts.models.professor_user import ProfessorUser
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication, FacultyApplicationTimelineEvent
from apps.authentication.services.portal_url_service import PortalURLService
from apps.faculty.models import SavedVacancy
from apps.it_recruitment.services.jobseeker_portal_helpers import format_salary_lpa
from apps.notifications.models import Notification


UNDER_REVIEW_STATUSES = {
    FacultyApplicationStatus.UNDER_REVIEW,
    FacultyApplicationStatus.SHORTLISTED,
    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
    FacultyApplicationStatus.DEPARTMENT_REVIEW,
    FacultyApplicationStatus.PRINCIPAL_REVIEW,
    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
}
SHORTLISTED_STATUSES = {
    FacultyApplicationStatus.SHORTLISTED,
    FacultyApplicationStatus.DEPARTMENT_REVIEW,
    FacultyApplicationStatus.PRINCIPAL_REVIEW,
    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
}
SELECTED_STATUSES = {
    FacultyApplicationStatus.OFFER_ACCEPTED,
    FacultyApplicationStatus.JOINED,
}


@dataclass
class StatCard:
    key: str
    label: str
    value: str
    icon: str
    tone: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "icon": self.icon,
            "tone": self.tone,
        }


@dataclass
class TrackerStat:
    key: str
    label: str
    value: int
    tone: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "tone": self.tone,
        }


@dataclass
class RecommendedJobCard:
    id: str
    title: str
    institution_name: str
    location: str
    logo_url: str | None
    tags: list[str]
    apply_url: str
    detail_url: str
    save_url: str
    is_saved: bool
    subject: str = "Faculty"
    salary: str = "Not disclosed"
    employment_type: str = "Full-time"
    experience_required: str = "Flexible"
    posted_date: str = "Recently"
    match_percentage: int = 85
    match_explanation: str = ""
    is_eligible: bool = True
    eligibility_message: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "institution_name": self.institution_name,
            "location": self.location,
            "logo_url": self.logo_url,
            "tags": self.tags,
            "apply_url": self.apply_url,
            "detail_url": self.detail_url,
            "save_url": self.save_url,
            "is_saved": self.is_saved,
            "subject": self.subject,
            "salary": self.salary,
            "employment_type": self.employment_type,
            "experience_required": self.experience_required,
            "posted_date": self.posted_date,
            "match_percentage": self.match_percentage,
            "match_explanation": self.match_explanation,
            "is_eligible": self.is_eligible,
            "eligibility_message": self.eligibility_message,
        }


@dataclass
class ApplicationRow:
    id: str
    institution_name: str
    job_title: str
    applied_date: str
    status_label: str
    status_class: str
    detail_url: str
    job_url: str
    department: str = "Faculty Department"
    receipt_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "institution_name": self.institution_name,
            "job_title": self.job_title,
            "applied_date": self.applied_date,
            "status_label": self.status_label,
            "status_class": self.status_class,
            "detail_url": self.detail_url,
            "job_url": self.job_url,
            "department": self.department,
            "receipt_url": self.receipt_url,
        }


@dataclass
class InterviewItem:
    id: str
    title: str
    institution_name: str
    schedule_label: str
    month_label: str
    day_label: str
    meet_url: str | None
    location_label: str | None
    detail_url: str
    round_label: str = "Technical Round"
    interview_type: str = "Online"
    date_label: str = ""
    time_label: str = ""
    status_label: str = "Scheduled"
    calendar_url: str = ""
    is_urgent: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "institution_name": self.institution_name,
            "schedule_label": self.schedule_label,
            "month_label": self.month_label,
            "day_label": self.day_label,
            "meet_url": self.meet_url,
            "location_label": self.location_label,
            "detail_url": self.detail_url,
            "round_label": self.round_label,
            "interview_type": self.interview_type,
            "date_label": self.date_label,
            "time_label": self.time_label,
            "status_label": self.status_label,
            "calendar_url": self.calendar_url,
            "is_urgent": self.is_urgent,
        }


@dataclass
class NotificationItem:
    id: str
    title: str
    body: str
    is_read: bool
    created_at: str
    icon: str
    tone: str
    mark_read_url: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "is_read": self.is_read,
            "created_at": self.created_at,
            "icon": self.icon,
            "tone": self.tone,
            "mark_read_url": self.mark_read_url,
        }


@dataclass
class QuickAction:
    key: str
    label: str
    icon: str
    url: str
    tone: str = "primary"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "icon": self.icon,
            "url": self.url,
            "tone": self.tone,
        }


class ProfessorDashboardPortalService:
    RECENT_APPLICATION_LIMIT = 8
    NOTIFICATION_LIMIT = 6
    INTERVIEW_LIMIT = 5

    def build(
        self, *, user: ProfessorUser, profile: ProfessorProfile | None = None
    ) -> dict:
        profile = profile or self._load_profile(user)
        now = timezone.localtime()
        greeting = greeting_for_hour(now.hour)
        display_name = profile.full_name if profile else user.email.split("@")[0]

        if profile is None:
            return self._empty_context(user, greeting, display_name)

        applications_qs = FacultyApplication.objects.filter(
            professor=profile, is_deleted=False
        ).select_related(
            "vacancy", "college", "vacancy__college", "vacancy__college__logo_file"
        )

        saved_count = SavedVacancy.objects.filter(
            professor=profile, is_deleted=False
        ).count()
        completion_svc = ProfessorProfileCompletionService()
        completion = (
            completion_svc.recalculate(profile)
            if not profile.profile_completion_fingerprint
            else completion_svc.get_dashboard_state(profile)
        )
        headline_parts = [
            p for p in [profile.current_designation, profile.current_institution] if p
        ]

        notifications, unread_count = self._notifications(user)

        return {
            "greeting": greeting,
            "display_name": display_name,
            "headline": profile.current_designation
            or profile.specialization
            or "Faculty Job Seeker",
            "subheadline": " • ".join(headline_parts)
            if headline_parts
            else (profile.specialization or ""),
            "avatar_url": media_url(profile.profile_photo),
            "stats": [
                s.to_dict()
                for s in self._top_stats(profile, applications_qs, saved_count)
            ],
            "tracker_stats": [
                s.to_dict() for s in self._tracker_stats(applications_qs)
            ],
            "completion": completion.to_dict(),
            "show_completion_card": completion.show_completion_card,
            "profile_completion": completion.percentage,
            "recommended_jobs": [
                j.to_dict() for j in self._recommended_jobs(profile, user)
            ],
            "recent_applications": [
                a.to_dict() for a in self._recent_applications(applications_qs, user)
            ],
            "upcoming_interviews": [
                i.to_dict() for i in self._upcoming_interviews(applications_qs, user)
            ],
            "notifications": [n.to_dict() for n in notifications],
            "unread_notification_count": unread_count,
            "saved_jobs_count": saved_count,
            "show_saved_empty": saved_count == 0,
            "quick_actions": [q.to_dict() for q in self._quick_actions(user)],
            "has_profile": True,
            "offer_letters_count": applications_qs.filter(
                status__in=[
                    FacultyApplicationStatus.OFFER_RELEASED,
                    FacultyApplicationStatus.OFFER_ACCEPTED,
                ]
            ).count(),
        }

    @staticmethod
    def _load_profile(user: ProfessorUser) -> ProfessorProfile | None:
        return (
            ProfessorProfile.objects.filter(user=user, is_deleted=False)
            .select_related("profile_photo", "cv_file", "user")
            .prefetch_related("qualifications", "departments__department")
            .first()
        )

    def _empty_context(self, user, greeting, display_name) -> dict:
        return {
            "greeting": greeting,
            "display_name": display_name,
            "headline": "Faculty Job Seeker",
            "subheadline": "Complete your profile to unlock personalized recommendations.",
            "avatar_url": None,
            "stats": [],
            "tracker_stats": [],
            "completion": {
                "percentage": 0,
                "status_label": "Getting Started",
                "checklist": [],
            },
            "recommended_jobs": [],
            "recent_applications": [],
            "upcoming_interviews": [],
            "notifications": [],
            "unread_notification_count": 0,
            "saved_jobs_count": 0,
            "show_saved_empty": True,
            "quick_actions": [
                QuickAction(
                    "complete_profile",
                    "Complete Profile",
                    "bi-person-check",
                    PortalURLService.professor(user, "professor_profile"),
                ).to_dict(),
                QuickAction(
                    "browse_jobs",
                    "Browse Faculty Jobs",
                    "bi-search",
                    PortalURLService.professor(user, "professor_browse_jobs"),
                ).to_dict(),
            ],
            "has_profile": False,
            "offer_letters_count": 0,
        }

    def _top_stats(self, profile, applications_qs, saved_count) -> list[StatCard]:
        views = Notification.objects.filter(
            recipient_domain="professor",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
        ).count()
        interviews = applications_qs.filter(status__in=INTERVIEW_STATUSES).count()
        return [
            StatCard(
                "applied",
                "Applied Jobs",
                str(applications_qs.count()),
                "bi-send",
                "primary",
            ),
            StatCard(
                "saved", "Saved Jobs", str(saved_count), "bi-bookmark", "secondary"
            ),
            StatCard("views", "Profile Views", str(views), "bi-eye", "tertiary"),
            StatCard(
                "interviews", "Interviews", str(interviews), "bi-chat-dots", "accent"
            ),
        ]

    def _tracker_stats(self, applications_qs) -> list[TrackerStat]:
        counts: dict[str, int] = {}
        for row in applications_qs.values("status").annotate(total=Count("id")):
            counts[row["status"]] = row["total"]
        total = sum(counts.values())
        return [
            TrackerStat("total", "Total Applied", total, "primary"),
            TrackerStat(
                "under_review",
                "Under Review",
                sum(counts.get(s, 0) for s in UNDER_REVIEW_STATUSES),
                "info",
            ),
            TrackerStat(
                "shortlisted",
                "Shortlisted",
                sum(counts.get(s, 0) for s in SHORTLISTED_STATUSES),
                "success",
            ),
            TrackerStat(
                "interview",
                "Interview Scheduled",
                sum(counts.get(s, 0) for s in INTERVIEW_STATUSES),
                "info",
            ),
            TrackerStat(
                "selected",
                "Selected",
                sum(counts.get(s, 0) for s in SELECTED_STATUSES),
                "success",
            ),
            TrackerStat(
                "rejected",
                "Rejected",
                counts.get(FacultyApplicationStatus.REJECTED, 0),
                "danger",
            ),
        ]

    def _recommended_jobs(self, profile, user) -> list[RecommendedJobCard]:
        recommender = ProfessorVacancyRecommendationService()
        saved_ids = recommender.saved_vacancy_ids(profile)
        cards = []
        for vacancy in recommender.recommend(profile):
            college = vacancy.college
            logo = (
                media_url(college.logo_file)
                if college and college.logo_file_id
                else None
            )
            location = _format_location(vacancy)
            salary = _format_salary(vacancy)
            employment = (
                vacancy.get_employment_type_display()
                if vacancy.employment_type
                else "Full-time"
            )
            experience = _format_experience(vacancy)
            subject = vacancy.department or vacancy.specialization_required or "Faculty"
            match_pct = getattr(vacancy, "match_percentage", 85)
            match_expl = getattr(vacancy, "match_explanation", "")
            
            from apps.academic_recruitment.services.faculty_application_eligibility_service import FacultyApplicationEligibilityService
            eligibility = FacultyApplicationEligibilityService().check(profile, vacancy)
            
            cards.append(
                RecommendedJobCard(
                    id=str(vacancy.pk),
                    title=vacancy.title,
                    institution_name=vacancy.college_name_snapshot
                    or (college.name if college else ""),
                    location=location,
                    logo_url=logo,
                    tags=[
                        t
                        for t in [salary, employment, experience]
                        if t and t != "Not disclosed"
                    ],
                    apply_url=PortalURLService.professor(
                        user, "professor_apply_vacancy", vacancy_id=vacancy.pk
                    ),
                    detail_url=PortalURLService.professor(
                        user, "professor_vacancy_detail", vacancy_id=vacancy.pk
                    ),
                    save_url=PortalURLService.professor(
                        user, "professor_save_vacancy", vacancy_id=vacancy.pk
                    ),
                    is_saved=vacancy.pk in saved_ids,
                    subject=subject,
                    salary=salary,
                    employment_type=employment,
                    experience_required=experience,
                    posted_date=_relative_time(vacancy.published_at),
                    match_percentage=match_pct,
                    match_explanation=match_expl,
                    is_eligible=eligibility.eligible,
                    eligibility_message=eligibility.message,
                )
            )
        return cards

    def _recent_applications(self, applications_qs, user) -> list[ApplicationRow]:
        rows = []
        for app in applications_qs.order_by("-applied_at")[
            : self.RECENT_APPLICATION_LIMIT
        ]:
            label, css = faculty_status_ui(app.status)
            dept = (
                getattr(app, "department_snapshot", "")
                or getattr(app.vacancy, "department", "")
                or "Department not specified"
            )
            detail_url = PortalURLService.professor(
                user, "professor_application_detail", application_id=app.pk
            )
            rows.append(
                ApplicationRow(
                    id=str(app.pk),
                    institution_name=app.college_name_snapshot or "Institution",
                    job_title=app.vacancy_title_snapshot,
                    applied_date=date_format(
                        timezone.localtime(app.applied_at), "M j, Y"
                    ),
                    status_label=label,
                    status_class=css,
                    detail_url=detail_url,
                    job_url=PortalURLService.professor(
                        user, "professor_vacancy_detail", vacancy_id=app.vacancy_id
                    ),
                    department=dept,
                    receipt_url=detail_url,
                )
            )
        return rows

    def _upcoming_interviews(self, applications_qs, user) -> list[InterviewItem]:
        items = []
        for app in applications_qs.filter(
            status=FacultyApplicationStatus.INTERVIEW_SCHEDULED
        ).order_by("-status_changed_at")[: self.INTERVIEW_LIMIT]:
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
            scheduled_at = meta.get("scheduled_at") or meta.get("interview_at")
            if scheduled_at:
                from django.utils.dateparse import parse_datetime

                parsed = parse_datetime(str(scheduled_at))
                if parsed:
                    dt = (
                        timezone.localtime(parsed)
                        if timezone.is_aware(parsed)
                        else timezone.make_aware(parsed)
                    )

            round_lbl = (
                meta.get("round")
                or meta.get("interview_round")
                or "Technical / Panel Round"
            )
            int_type = meta.get("type") or meta.get("interview_type") or "Online"
            date_lbl = dt.strftime("%b %d, %Y")
            time_lbl = dt.strftime("%I:%M %p").lstrip("0")
            is_urg = 0 <= (dt - timezone.now()).total_seconds() <= 86400

            start_iso = dt.strftime("%Y%m%dT%H%M%SZ")
            end_iso = (dt + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")
            cal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Faculty+Interview:+{app.vacancy_title_snapshot}&dates={start_iso}/{end_iso}&details=Interview+with+{app.college_name_snapshot}"

            items.append(
                InterviewItem(
                    id=str(app.pk),
                    title=app.vacancy_title_snapshot,
                    institution_name=app.college_name_snapshot,
                    schedule_label=time_lbl,
                    month_label=dt.strftime("%b").upper(),
                    day_label=str(dt.day),
                    meet_url=meta.get("meeting_link")
                    or meta.get("meet_url")
                    or meta.get("join_url"),
                    location_label=meta.get("location") or meta.get("venue"),
                    detail_url=PortalURLService.professor(
                        user, "professor_application_detail", application_id=app.pk
                    ),
                    round_label=round_lbl,
                    interview_type=int_type,
                    date_label=date_lbl,
                    time_label=time_lbl,
                    status_label="Confirmed",
                    calendar_url=cal_url,
                    is_urgent=is_urg,
                )
            )
        return items

    def _notifications(self, user) -> tuple[list[NotificationItem], int]:
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        qs = Notification.objects.filter(
            recipient_domain="professor", recipient_id=user.pk
        ).order_by("-created_at")
        unread = Notification.objects.filter(
            recipient_domain="professor", recipient_id=user.pk, is_read=False
        ).count()
        items = []
        for note in qs[: self.NOTIFICATION_LIMIT]:
            icon, tone = _notification_style(note.event_type)
            items.append(
                NotificationItem(
                    id=str(note.pk),
                    title=note.title,
                    body=note.body,
                    is_read=note.is_read,
                    created_at=_relative_time(note.created_at),
                    icon=icon,
                    tone=tone,
                    mark_read_url=pu(
                        "professor_notification_read", notification_id=note.pk
                    ),
                )
            )
        return items, unread

    def _quick_actions(self, user) -> list[QuickAction]:
        return [
            QuickAction(
                "upload_resume",
                "Upload Resume",
                "bi-upload",
                PortalURLService.professor(user, "professor_resume"),
                "primary",
            ),
            QuickAction(
                "add_exp",
                "Add Exp.",
                "bi-mortarboard",
                PortalURLService.professor(user, "professor_profile"),
                "secondary",
            ),
            QuickAction(
                "search_jobs",
                "Search Jobs",
                "bi-search",
                PortalURLService.professor(user, "professor_browse_jobs"),
                "tertiary",
            ),
            QuickAction(
                "saved_jobs",
                "Saved Jobs",
                "bi-bookmark",
                PortalURLService.professor(user, "professor_saved_jobs"),
                "muted",
            ),
        ]


def _format_location(vacancy) -> str:
    parts = [p for p in [vacancy.city, vacancy.state, vacancy.country] if p]
    return ", ".join(parts) if parts else "Location not specified"


def _format_salary(vacancy) -> str:
    if vacancy.salary_min or vacancy.salary_max:
        return format_salary_lpa(
            vacancy.salary_min, vacancy.salary_max, vacancy.salary_currency or "INR"
        )
    return "Not disclosed"


def _format_experience(vacancy) -> str:
    if vacancy.experience_min and vacancy.experience_max:
        return f"{vacancy.experience_min}-{vacancy.experience_max} yrs Exp"
    if vacancy.experience_min:
        return f"{vacancy.experience_min}+ yrs Exp"
    return "Experience flexible"


def _relative_time(dt) -> str:
    if not dt:
        return ""
    delta = timezone.now() - dt
    if delta < timedelta(hours=1):
        return f"{max(1, int(delta.total_seconds() // 60))} min ago"
    if delta < timedelta(hours=24):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if delta < timedelta(days=7):
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    return date_format(timezone.localtime(dt), "M j, Y")


def _notification_style(event_type: str) -> tuple[str, str]:
    return {
        "profile_viewed": ("bi-eye", "primary"),
        "interview_scheduled": ("bi-calendar-event", "info"),
        "application_shortlisted": ("bi-star", "success"),
        "offer_released": ("bi-envelope-check", "success"),
    }.get(event_type, ("bi-bell", "primary"))
