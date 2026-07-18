"""Institution recruiter notifications portal service."""

from __future__ import annotations

from dataclasses import dataclass
import re

from django.db.models import Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.formats import date_format

from apps.accounts.models.college_user import CollegeUser
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.notifications.models import Notification


@dataclass
class NotificationRow:
    id: str
    title: str
    body: str
    event_type: str
    event_label: str
    is_read: bool
    created_at: str
    icon: str
    tone: str
    mark_read_url: str
    action_url: str
    action_label: str
    candidate_name: str = ""
    vacancy_title: str = ""
    candidate_email: str = ""
    candidate_phone: str = ""
    email_url: str = ""
    whatsapp_url: str = ""
    channels_label: str = "Internal"


@dataclass
class NotificationsPageContext:
    notifications: list[NotificationRow]
    unread_count: int
    read_count: int
    page: int
    total_pages: int
    total_count: int
    event_filters: list[dict]
    selected_event: str
    selected_state: str


def _notification_style(event_type: str) -> tuple[str, str, str]:
    return {
        "new_application": ("bi-person-plus", "success", "New Application"),
        "application_updated": ("bi-arrow-repeat", "info", "Application Updated"),
        "interview_scheduled": ("bi-calendar-event", "info", "Interview Scheduled"),
        "interview_completed": ("bi-check2-circle", "success", "Interview Completed"),
        "offer_released": ("bi-envelope-check", "success", "Offer Released"),
        "offer_accepted": ("bi-envelope-heart", "success", "Offer Accepted"),
        "offer_declined": ("bi-envelope-x", "danger", "Offer Declined"),
        "faculty_message": ("bi-chat", "info", "Message"),
        "verification_update": ("bi-patch-check", "primary", "Verification Update"),
        "vacancy_published": ("bi-megaphone", "primary", "Vacancy Published"),
        "job_expiring": ("bi-hourglass-split", "warning", "Job Expiring"),
        "profile_viewed": ("bi-eye", "secondary", "Profile Viewed"),
        "resume_updated": ("bi-file-earmark-arrow-up", "accent", "Resume Updated"),
    }.get(event_type, ("bi-bell", "primary", "Update"))


class CollegeNotificationsPortalService(BaseService):
    PAGE_SIZE = 15

    def list_notifications(
        self, user: CollegeUser, *, page: int = 1, event: str = "", state: str = "all"
    ) -> NotificationsPageContext:
        cu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        base_qs = Notification.objects.filter(
            recipient_domain="college", recipient_id=user.pk, is_deleted=False
        ).order_by("-created_at")
        qs = self._apply_filters(base_qs, event=event, state=state)
        unread = qs.filter(is_read=False).count()
        read_count = qs.filter(is_read=True).count()
        paginator = Paginator(qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)

        rows = []
        for note in page_obj.object_list:
            icon, tone, label = _notification_style(note.event_type)
            action_url, action_label = self._action_for_notification(user, note, cu=cu)
            rows.append(
                NotificationRow(
                    id=str(note.pk),
                    title=note.title,
                    body=note.body,
                    event_type=note.event_type,
                    event_label=label,
                    is_read=note.is_read,
                    created_at=self._relative_time(note.created_at),
                    icon=icon,
                    tone=tone,
                    mark_read_url=cu(
                        "college_notification_read", notification_id=note.pk
                    ),
                    action_url=action_url,
                    action_label=action_label,
                )
            )

        return NotificationsPageContext(
            notifications=rows,
            unread_count=unread,
            read_count=read_count,
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
            event_filters=self._event_filters(base_qs),
            selected_event=event,
            selected_state=state,
        )

    def list_messages(
        self, user: CollegeUser, *, page: int = 1, state: str = "all"
    ) -> NotificationsPageContext:
        cu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        base_qs = (
            Notification.objects.filter(
                recipient_domain="college", recipient_id=user.pk
            )
            .filter(event_type__icontains="message")
            .filter(is_deleted=False)
            .order_by("-created_at")
        )
        qs = self._apply_filters(base_qs, event="", state=state)
        unread = qs.filter(is_read=False).count()
        read_count = qs.filter(is_read=True).count()
        paginator = Paginator(qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)
        direct_contact_allowed = bool(
            getattr(
                getattr(user, "account_settings", None),
                "allow_direct_applicant_contact",
                True,
            )
        )
        app_ids = []
        for note in page_obj.object_list:
            app_id = self._extract_application_id(note)
            if app_id:
                app_ids.append(app_id)
        app_map = {
            str(app.pk): app
            for app in FacultyApplicationSelector()
            .for_college_user(user)
            .filter(pk__in=app_ids)
            .select_related("professor", "professor__user", "vacancy")
        }
        rows = []
        for note in page_obj.object_list:
            action_url, action_label = self._action_for_notification(user, note, cu=cu)
            candidate_name = ""
            vacancy_title = ""
            candidate_email = ""
            candidate_phone = ""
            email_url = ""
            whatsapp_url = ""
            channels = ["Internal"]
            app_id = self._extract_application_id(note)
            app = app_map.get(str(app_id)) if app_id else None
            if app:
                candidate_name = app.applicant_name_snapshot or "Faculty Applicant"
                vacancy_title = app.vacancy_title_snapshot or "Faculty Role"
                professor_user = getattr(getattr(app, "professor", None), "user", None)
                candidate_email = (getattr(professor_user, "email", "") or "").strip()
                candidate_phone = (getattr(app.professor, "phone", "") or "").strip()
            payload = note.payload or {}
            if not candidate_email:
                candidate_email = str(
                    payload.get("candidate_email") or payload.get("email") or ""
                ).strip()
            if not candidate_phone:
                candidate_phone = str(
                    payload.get("candidate_phone") or payload.get("phone") or ""
                ).strip()
            if direct_contact_allowed and candidate_email:
                email_url = f"mailto:{candidate_email}"
                channels.append("Email")
            if direct_contact_allowed:
                whatsapp_url = self._whatsapp_url(candidate_phone)
                if whatsapp_url:
                    channels.append("WhatsApp")
            rows.append(
                NotificationRow(
                    id=str(note.pk),
                    title=note.title,
                    body=note.body,
                    event_type=note.event_type,
                    event_label="Message",
                    is_read=note.is_read,
                    created_at=self._relative_time(note.created_at),
                    icon="bi-chat",
                    tone="info",
                    mark_read_url=cu(
                        "college_notification_read", notification_id=note.pk
                    ),
                    action_url=action_url,
                    action_label=action_label,
                    candidate_name=candidate_name,
                    vacancy_title=vacancy_title,
                    candidate_email=candidate_email,
                    candidate_phone=candidate_phone,
                    email_url=email_url,
                    whatsapp_url=whatsapp_url,
                    channels_label=" / ".join(channels),
                )
            )
        return NotificationsPageContext(
            notifications=rows,
            unread_count=unread,
            read_count=read_count,
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
            event_filters=[],
            selected_event="",
            selected_state=state,
        )

    @staticmethod
    def _apply_filters(qs, *, event: str, state: str):
        if event:
            qs = qs.filter(event_type=event)
        if state == "unread":
            qs = qs.filter(is_read=False)
        elif state == "read":
            qs = qs.filter(is_read=True)
        return qs

    @staticmethod
    def _action_for_notification(user, note, *, cu) -> tuple[str, str]:
        event = (note.event_type or "").lower()
        entity_type = (note.entity_type or "").lower()
        entity_id = note.entity_id

        if entity_id and entity_type in {"application", "faculty_application"}:
            if (
                FacultyApplicationSelector()
                .for_college_user(user)
                .filter(pk=entity_id)
                .exists()
            ):
                return cu(
                    "college_application_detail", application_id=entity_id
                ), "Open Application"
        if entity_id and entity_type in {"vacancy", "faculty_vacancy"}:
            return cu("college_vacancies"), "Open Vacancy"
        if "interview" in event:
            return cu("college_interviews"), "Open Interviews"
        if "offer" in event or "application" in event:
            return cu("college_applications"), "Open Applications"
        if "message" in event:
            return cu("college_messages"), "Open Messages"
        if "verification" in event or "profile" in event:
            return cu("college_profile"), "Open Profile"
        return cu("college_notifications"), "Open Center"

    @staticmethod
    def _extract_application_id(note):
        if note.entity_id and (note.entity_type or "").lower() in {
            "application",
            "faculty_application",
        }:
            return note.entity_id
        payload = note.payload or {}
        return payload.get("application_id") or payload.get("faculty_application_id")

    @staticmethod
    def _whatsapp_url(phone: str) -> str:
        digits = re.sub(r"\D+", "", str(phone or ""))
        if not digits:
            return ""
        if len(digits) == 10:
            digits = f"91{digits}"
        return f"https://wa.me/{digits}"

    @staticmethod
    def _event_filters(base_qs) -> list[dict]:
        rows = (
            base_qs.values("event_type")
            .annotate(count=Count("id"))
            .order_by("-count", "event_type")[:8]
        )
        filters = []
        for row in rows:
            event = row.get("event_type") or ""
            if not event:
                continue
            _, _, label = _notification_style(event)
            filters.append(
                {"value": event, "label": label, "count": int(row.get("count") or 0)}
            )
        return filters

    @staticmethod
    def _relative_time(dt) -> str:
        if not dt:
            return ""
        from datetime import timedelta

        delta = timezone.now() - dt
        if delta < timedelta(hours=1):
            mins = max(1, int(delta.total_seconds() // 60))
            return f"{mins} min ago"
        if delta < timedelta(hours=24):
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        if delta < timedelta(days=7):
            days = delta.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        return date_format(timezone.localtime(dt), "M j, Y")
