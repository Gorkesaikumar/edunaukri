"""IT Job Seeker messages portal — selection alerts and recruiter messages."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.formats import date_format

from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.notifications.models import Notification


def _icon_for_event(event_type: str) -> tuple[str, str]:
    """Return (bootstrap-icon-class, css-tone) for a given event_type."""
    return {
        "recruiter_message": ("bi-stars", "success"),
        "institution_message": ("bi-stars", "success"),
        "application.status_changed": ("bi-activity", "primary"),
        "interview_scheduled": ("bi-calendar-event", "info"),
        "offer_released": ("bi-envelope-check", "success"),
        "profile_viewed": ("bi-eye", "secondary"),
    }.get(event_type, ("bi-bell", "primary"))


@dataclass
class MessageRow:
    id: str
    title: str
    body: str
    is_read: bool
    created_at: str
    icon: str
    tone: str
    event_type: str


@dataclass
class MessagesPageContext:
    messages: list[MessageRow]
    unread_count: int
    page: int
    total_pages: int
    total_count: int


class JobSeekerMessagesPortalService(BaseService):
    """Lists messages (recruiter-sent notifications) for an IT job seeker."""

    PAGE_SIZE = 20

    def list_messages(self, user, *, page: int = 1) -> MessagesPageContext:
        qs = (
            Notification.objects.filter(
                recipient_domain="it",
                recipient_id=user.pk,
                is_deleted=False,
            )
            .filter(event_type__in=["recruiter_message", "institution_message"])
            .order_by("-created_at")
        )

        unread = qs.filter(is_read=False).count()
        paginator = Paginator(qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)

        rows: list[MessageRow] = []
        for note in page_obj.object_list:
            icon, tone = _icon_for_event(note.event_type)
            rows.append(
                MessageRow(
                    id=str(note.pk),
                    title=note.title,
                    body=note.body or "",
                    is_read=note.is_read,
                    created_at=self._relative_time(note.created_at),
                    icon=icon,
                    tone=tone,
                    event_type=note.event_type,
                )
            )

        return MessagesPageContext(
            messages=rows,
            unread_count=unread,
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
        )

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
