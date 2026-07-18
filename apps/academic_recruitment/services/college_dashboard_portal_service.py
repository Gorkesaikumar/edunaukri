"""Aggregate dashboard data for the Institution (College) recruiter portal."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models.college_user import CollegeUser
from apps.academic_recruitment.services.college_portal_helpers import (
    greeting_for_hour,
    institution_status_ui,
    primary_institution_for_user,
)
from apps.academic_recruitment.services.college_profile_portal_service import (
    CollegeProfilePortalService,
)
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplicationTimelineEvent
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.dashboard.selectors.dashboard_selector import DashboardSelector
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.selectors.vacancy_dashboard import VacancyDashboardSelector
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.notifications.models import Notification


PIPELINE_BUCKETS = (
    {
        "key": "applied",
        "label": "New Applications",
        "tone": "info",
        "statuses": (FacultyApplicationStatus.APPLIED,),
    },
    {
        "key": "review",
        "label": "Under Review",
        "tone": "secondary",
        "statuses": (
            FacultyApplicationStatus.UNDER_REVIEW,
            FacultyApplicationStatus.ACADEMIC_VERIFICATION,
            FacultyApplicationStatus.DEPARTMENT_REVIEW,
            FacultyApplicationStatus.PRINCIPAL_REVIEW,
            FacultyApplicationStatus.MANAGEMENT_APPROVAL,
        ),
    },
    {
        "key": "interview",
        "label": "Interviews",
        "tone": "accent",
        "statuses": (
            FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            FacultyApplicationStatus.INTERVIEW_COMPLETED,
        ),
    },
    {
        "key": "offer",
        "label": "Offers",
        "tone": "primary",
        "statuses": (
            FacultyApplicationStatus.OFFER_RELEASED,
            FacultyApplicationStatus.OFFER_ACCEPTED,
            FacultyApplicationStatus.OFFER_DECLINED,
        ),
    },
    {
        "key": "joined",
        "label": "Joined",
        "tone": "success",
        "statuses": (FacultyApplicationStatus.JOINED,),
    },
)


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


class CollegeDashboardPortalService:
    RECENT_APPLICATION_LIMIT = 8
    ACTIVE_VACANCY_LIMIT = 5

    def build(self, *, user: CollegeUser) -> dict:
        now = timezone.localtime()
        institution = primary_institution_for_user(user)
        display_name = institution["name"] if institution else user.email.split("@")[0]
        greeting = greeting_for_hour(now.hour)
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)

        if not CollegeMemberSelector().has_active_membership(user):
            return self._empty_context(user, greeting, display_name, pu)

        summary = DashboardSelector().college_summary(user)
        vacancy_stats = VacancyDashboardSelector().college_user_summary(user)
        app_stats = FacultyApplicationStatisticsService().college_dashboard(user)
        apps_qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .select_related(
                "vacancy",
                "professor",
            )
        )
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = apps_qs.filter(applied_at__gte=today_start).count()
        by_status = app_stats.get("applications_by_status") or {}
        total_applications = app_stats.get("total_applications", 0)
        total_or_one = total_applications or 1
        published_count = vacancy_stats.get("published_vacancies", 0)
        draft_count = vacancy_stats.get("draft_vacancies", 0)
        closed_outcomes = by_status.get(
            FacultyApplicationStatus.JOINED, 0
        ) + by_status.get(
            FacultyApplicationStatus.REJECTED,
            0,
        )
        pending_review = sum(
            by_status.get(status, 0)
            for status in (
                FacultyApplicationStatus.UNDER_REVIEW,
                FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                FacultyApplicationStatus.DEPARTMENT_REVIEW,
                FacultyApplicationStatus.PRINCIPAL_REVIEW,
                FacultyApplicationStatus.MANAGEMENT_APPROVAL,
            )
        )
        interviews_scheduled = by_status.get(
            FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0
        )
        interviews_completed = by_status.get(
            FacultyApplicationStatus.INTERVIEW_COMPLETED, 0
        )
        offers_released = by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
        offers_accepted = by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0)
        joined = by_status.get(FacultyApplicationStatus.JOINED, 0)
        profile_context = CollegeProfilePortalService().build(user)
        notifications_bundle = self._recent_notifications(user, pu)

        return {
            "greeting": greeting,
            "display_name": display_name,
            "headline": institution["name"] if institution else "Institution Recruiter",
            "subheadline": self._subheadline(institution),
            "institution": institution,
            "has_institution": institution is not None,
            "stats": [
                s.to_dict()
                for s in self._top_stats(summary, vacancy_stats, app_stats, new_today)
            ],
            "overview_stats": [
                {
                    "key": "active_jobs",
                    "label": "Active Jobs",
                    "value": published_count,
                    "trend": "+12%",
                },
                {
                    "key": "draft_jobs",
                    "label": "Draft Jobs",
                    "value": draft_count,
                    "trend": "In queue",
                },
                {
                    "key": "closed_outcomes",
                    "label": "Closed Outcomes",
                    "value": closed_outcomes,
                    "trend": "Joined + Rejected",
                },
                {
                    "key": "total_applications",
                    "label": "Total Applications",
                    "value": total_applications,
                    "trend": f"+{new_today} today",
                },
                {
                    "key": "interviews_scheduled",
                    "label": "Interviews Scheduled",
                    "value": interviews_scheduled,
                    "trend": "Upcoming",
                },
                {
                    "key": "offers_sent",
                    "label": "Offers Sent",
                    "value": offers_released,
                    "trend": f"{offers_accepted} accepted",
                },
                {
                    "key": "hired_candidates",
                    "label": "Hired Candidates",
                    "value": joined,
                    "trend": "Joined",
                },
                {
                    "key": "pending_review",
                    "label": "Pending Review",
                    "value": pending_review,
                    "trend": "Needs action",
                },
            ],
            "recent_applications": self._recent_applications(apps_qs, pu),
            "active_vacancies": self._active_vacancies(user, pu),
            "upcoming_interviews": self._upcoming_interviews(apps_qs, pu),
            "offer_management": self._offer_management(apps_qs, pu),
            "notifications": notifications_bundle["items"],
            "messages": notifications_bundle["messages"],
            "profile_analytics": {
                "profile_completion": profile_context.profile_completion,
                "profile_completion_state": profile_context.profile_completion_state,
                "active_applications": app_stats.get("active_applications", 0),
                "interview_rate": round(
                    ((interviews_scheduled + interviews_completed) / total_or_one) * 100
                ),
                "offer_rate": round(
                    ((offers_released + offers_accepted) / total_or_one) * 100
                ),
                "hiring_rate": round((joined / total_or_one) * 100),
            },
            "institution_profile": {
                "name": institution.get("name", "") if institution else "",
                "city": institution.get("city", "") if institution else "",
                "verified": bool(institution and institution.get("verified")),
                "verification_label": institution.get("verification_label", "")
                if institution
                else "",
                "can_publish": bool(institution and institution.get("can_publish")),
                "profile_completion": profile_context.profile_completion,
                "profile_completion_state": profile_context.profile_completion_state,
            },
            "quick_actions": self._quick_actions(pu, institution),
            "urls": {
                "post_vacancy": pu("college_vacancy_create"),
                "vacancies": pu("college_vacancies"),
                "applications": pu("college_applications"),
                "interviews": pu("college_interviews"),
                "profile": pu("college_profile"),
                "messages": pu("college_messages"),
                "notifications": pu("college_notifications"),
                "settings": pu("college_settings"),
                "analytics": pu("college_analytics"),
                "insights": pu("college_dashboard_insights_api"),
            },
        }

    @staticmethod
    def _subheadline(institution: dict | None) -> str:
        if not institution:
            return "Set up your institution profile to start hiring faculty."
        parts = [
            p
            for p in [institution.get("city"), institution.get("verification_label")]
            if p
        ]
        verified = (
            "Verified institution"
            if institution.get("verified")
            else "Verification pending"
        )
        if institution.get("verified"):
            parts.insert(0, verified)
        else:
            parts.append(verified)
        return " • ".join(parts)

    def _empty_context(self, user, greeting, display_name, pu) -> dict:
        return {
            "greeting": greeting,
            "display_name": display_name,
            "headline": "Institution Recruiter",
            "subheadline": "Create your institution profile to publish faculty vacancies.",
            "institution": None,
            "has_institution": False,
            "stats": [],
            "overview_stats": [],
            "pipeline": [],
            "pipeline_view": [],
            "recent_applications": [],
            "active_vacancies": [],
            "upcoming_interviews": [],
            "offer_management": {
                "summary": [],
                "recent": [],
                "offers_url": pu("college_applications"),
            },
            "notifications": [],
            "messages": {"total": 0, "unread": 0, "url": pu("college_messages")},
            "profile_analytics": {
                "profile_completion": 0,
                "active_applications": 0,
                "interview_rate": 0,
                "offer_rate": 0,
                "hiring_rate": 0,
            },
            "institution_profile": {
                "name": "",
                "city": "",
                "verified": False,
                "verification_label": "",
                "can_publish": False,
                "profile_completion": 0,
            },
            "quick_actions": [
                {
                    "key": "setup_profile",
                    "label": "Set Up Institution",
                    "icon": "bi-building",
                    "url": pu("college_profile"),
                    "tone": "primary",
                }
            ],
            "urls": {
                "post_vacancy": pu("college_vacancy_create"),
                "vacancies": pu("college_vacancies"),
                "applications": pu("college_applications"),
                "interviews": pu("college_interviews"),
                "profile": pu("college_profile"),
                "messages": pu("college_messages"),
                "notifications": pu("college_notifications"),
                "settings": pu("college_settings"),
                "analytics": pu("college_analytics"),
                "insights": pu("college_dashboard_insights_api"),
            },
        }

    def _top_stats(
        self, summary, vacancy_stats, app_stats, new_today
    ) -> list[StatCard]:
        return [
            StatCard(
                "published_vacancies",
                "Published Vacancies",
                str(vacancy_stats.get("published_vacancies", 0)),
                "bi-mortarboard",
                "primary",
            ),
            StatCard(
                "applications_received",
                "Applications Received",
                str(
                    app_stats.get(
                        "total_applications", summary.get("applications_received", 0)
                    )
                ),
                "bi-people",
                "secondary",
            ),
            StatCard(
                "active_applications",
                "Active Applications",
                str(app_stats.get("active_applications", 0)),
                "bi-activity",
                "accent",
            ),
            StatCard(
                "new_today",
                "New Today",
                str(new_today),
                "bi-inbox",
                "tertiary",
            ),
        ]

    @staticmethod
    def _pipeline(by_status: dict) -> list[dict]:
        items = []
        for bucket in PIPELINE_BUCKETS:
            count = sum(by_status.get(status, 0) for status in bucket["statuses"])
            items.append(
                {
                    "key": bucket["key"],
                    "label": bucket["label"],
                    "value": count,
                    "tone": bucket["tone"],
                }
            )
        return items

    @staticmethod
    def _pipeline_view(by_status: dict) -> list[dict]:
        rows = [
            {
                "key": "applied",
                "label": "Applied",
                "value": by_status.get(FacultyApplicationStatus.APPLIED, 0),
                "tone": "primary",
            },
            {
                "key": "review",
                "label": "Academic Review",
                "value": sum(
                    by_status.get(status, 0)
                    for status in (
                        FacultyApplicationStatus.UNDER_REVIEW,
                        FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                        FacultyApplicationStatus.DEPARTMENT_REVIEW,
                        FacultyApplicationStatus.PRINCIPAL_REVIEW,
                        FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                    )
                ),
                "tone": "secondary",
            },
            {
                "key": "interview",
                "label": "Interview",
                "value": by_status.get(FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0)
                + by_status.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0),
                "tone": "accent",
            },
            {
                "key": "offer",
                "label": "Offer",
                "value": by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0),
                "tone": "success",
            },
            {
                "key": "joined",
                "label": "Joined",
                "value": by_status.get(FacultyApplicationStatus.JOINED, 0),
                "tone": "tertiary",
            },
        ]
        peak = max((row["value"] for row in rows), default=0) or 1
        for row in rows:
            row["pct"] = (
                max(6, round((row["value"] / peak) * 100)) if row["value"] else 0
            )
        return rows

    def _recent_applications(self, apps_qs, pu) -> list[dict]:
        rows = []
        for app in apps_qs.order_by("-applied_at")[: self.RECENT_APPLICATION_LIMIT]:
            status_label, status_class = institution_status_ui(app.status)
            profile_bits = [
                bool(app.cv_file_id),
                bool(app.current_designation),
                bool(app.current_institution),
                bool(app.department),
                bool(app.experience_snapshot),
            ]
            match_score = round(
                (sum(1 for bit in profile_bits if bit) / len(profile_bits)) * 100
            )
            rows.append(
                {
                    "id": str(app.pk),
                    "candidate": app.applicant_name_snapshot or "Faculty Applicant",
                    "vacancy_title": app.vacancy_title_snapshot or "Faculty Role",
                    "department": getattr(app, "department", "") or "",
                    "match_score": match_score,
                    "status_label": status_label,
                    "status_class": status_class,
                    "applied_label": timezone.localtime(app.applied_at).strftime(
                        "%b %d, %Y"
                    ),
                    "url": pu("college_application_detail", application_id=app.pk),
                    "list_url": pu("college_applications"),
                }
            )
        return rows

    def _active_vacancies(self, user, pu) -> list[dict]:
        vacancies = (
            FacultyVacancySelector()
            .for_college_user(user)
            .filter(status=VacancyStatus.PUBLISHED)
            .select_related("college")
            .order_by("-published_at", "-created_at")[: self.ACTIVE_VACANCY_LIMIT]
        )
        items = []
        for vacancy in vacancies:
            location = vacancy.city or vacancy.college_name_snapshot or "—"
            items.append(
                {
                    "id": str(vacancy.pk),
                    "title": vacancy.title,
                    "department": vacancy.department or "—",
                    "location": location,
                    "applications_count": vacancy.application_count,
                    "url": pu("college_vacancies"),
                }
            )
        return items

    def _upcoming_interviews(self, apps_qs, pu) -> list[dict]:
        app_ids = list(
            apps_qs.filter(
                status=FacultyApplicationStatus.INTERVIEW_SCHEDULED
            ).values_list("pk", flat=True)[:40]
        )
        if not app_ids:
            return []
        events = (
            FacultyApplicationTimelineEvent.objects.filter(
                application_id__in=app_ids,
                to_status=FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                is_deleted=False,
            )
            .select_related("application")
            .order_by("-occurred_at")
        )
        latest_by_app: dict[str, FacultyApplicationTimelineEvent] = {}
        for event in events:
            app_id = str(event.application_id)
            if app_id not in latest_by_app:
                latest_by_app[app_id] = event

        rows: list[dict] = []
        now = timezone.now()
        for event in latest_by_app.values():
            metadata = event.metadata or {}
            raw = metadata.get("scheduled_at") or metadata.get("interview_at")
            parsed = parse_datetime(str(raw)) if raw else None
            if not parsed:
                continue
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            if parsed < now:
                continue
            app = event.application
            rows.append(
                {
                    "application_id": str(app.pk),
                    "candidate": app.applicant_name_snapshot or "Faculty Applicant",
                    "vacancy_title": app.vacancy_title_snapshot or "Faculty Role",
                    "interview_type": metadata.get("interview_type") or "Interview",
                    "scheduled_at": parsed,
                    "scheduled_label": timezone.localtime(parsed).strftime(
                        "%b %d, %I:%M %p"
                    ),
                    "interviews_url": pu("college_interviews"),
                    "application_url": pu(
                        "college_application_detail", application_id=app.pk
                    ),
                }
            )
        rows.sort(key=lambda row: row["scheduled_at"])
        for row in rows:
            row.pop("scheduled_at", None)
        return rows[:5]

    def _offer_management(self, apps_qs, pu) -> dict:
        offer_qs = apps_qs.filter(
            status__in=(
                FacultyApplicationStatus.OFFER_RELEASED,
                FacultyApplicationStatus.OFFER_ACCEPTED,
                FacultyApplicationStatus.OFFER_DECLINED,
            )
        ).order_by("-status_changed_at", "-applied_at")
        pending = offer_qs.filter(
            status=FacultyApplicationStatus.OFFER_RELEASED
        ).count()
        accepted = offer_qs.filter(
            status=FacultyApplicationStatus.OFFER_ACCEPTED
        ).count()
        declined = offer_qs.filter(
            status=FacultyApplicationStatus.OFFER_DECLINED
        ).count()
        recent = []
        for app in offer_qs[:5]:
            if app.status == FacultyApplicationStatus.OFFER_ACCEPTED:
                tone = "success"
                status_label = "Accepted"
            elif app.status == FacultyApplicationStatus.OFFER_DECLINED:
                tone = "danger"
                status_label = "Declined"
            else:
                tone = "info"
                status_label = "Pending"
            recent.append(
                {
                    "candidate": app.applicant_name_snapshot or "Faculty Applicant",
                    "vacancy_title": app.vacancy_title_snapshot or "Faculty Role",
                    "status_label": status_label,
                    "tone": tone,
                    "updated_label": timezone.localtime(
                        app.status_changed_at or app.applied_at
                    ).strftime("%b %d, %I:%M %p"),
                    "application_url": pu(
                        "college_application_detail", application_id=app.pk
                    ),
                }
            )
        return {
            "summary": [
                {"label": "Pending", "value": pending, "tone": "info"},
                {"label": "Accepted", "value": accepted, "tone": "success"},
                {"label": "Declined", "value": declined, "tone": "danger"},
            ],
            "recent": recent,
            "offers_url": pu("college_applications"),
        }

    @staticmethod
    def _recent_notifications(user, pu) -> dict:
        base_qs = Notification.objects.filter(
            recipient_domain="college",
            recipient_id=user.pk,
            is_deleted=False,
        ).order_by("-created_at")
        notes = []
        for note in base_qs[:6]:
            notes.append(
                {
                    "id": str(note.pk),
                    "title": note.title,
                    "body": note.body,
                    "is_read": note.is_read,
                    "timestamp": timezone.localtime(note.created_at).strftime(
                        "%b %d, %I:%M %p"
                    ),
                    "url": pu("college_notifications"),
                }
            )
        messages = base_qs.filter(event_type__icontains="message")
        return {
            "items": notes,
            "messages": {
                "total": messages.count(),
                "unread": messages.filter(is_read=False).count(),
                "url": pu("college_messages"),
            },
        }

    @staticmethod
    def _quick_actions(pu, institution: dict | None) -> list[dict]:
        actions = [
            {
                "key": "post_vacancy",
                "label": "Post Vacancy",
                "icon": "bi-file-earmark-plus",
                "url": pu("college_vacancy_create"),
                "tone": "primary",
            },
            {
                "key": "review_applications",
                "label": "Review Applications",
                "icon": "bi-person-check",
                "url": pu("college_applications"),
                "tone": "secondary",
            },
        ]
        if institution and not institution.get("verified"):
            actions.append(
                {
                    "key": "complete_profile",
                    "label": "Complete Verification",
                    "icon": "bi-shield-check",
                    "url": pu("college_profile"),
                    "tone": "accent",
                }
            )
        return actions
