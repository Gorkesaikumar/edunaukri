"""Professor notifications portal service."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.formats import date_format

from apps.accounts.models.professor_user import ProfessorUser
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.notifications.models import Notification


@dataclass
class NotificationRow:
    id: str
    title: str
    body: str
    is_read: bool
    created_at: str
    icon: str
    tone: str
    mark_read_url: str


@dataclass
class NotificationsPageContext:
    notifications: list[NotificationRow]
    unread_count: int
    page: int
    total_pages: int
    total_count: int


def _notification_style(event_type: str) -> tuple[str, str]:
    return {
        "profile_viewed": ("bi-eye", "primary"),
        "interview_scheduled": ("bi-calendar-event", "info"),
        "application_shortlisted": ("bi-star", "success"),
        "offer_released": ("bi-envelope-check", "success"),
        "recruiter_message": ("bi-chat", "info"),
        "institution_message": ("bi-chat", "info"),
    }.get(event_type, ("bi-bell", "primary"))


class ProfessorNotificationsPortalService(BaseService):
    PAGE_SIZE = 15

    def list_notifications(
        self, user: ProfessorUser, *, page: int = 1
    ) -> NotificationsPageContext:
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        qs = Notification.objects.filter(
            recipient_domain="professor", recipient_id=user.pk
        ).order_by("-created_at")
        unread = qs.filter(is_read=False).count()
        paginator = Paginator(qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)

        rows = []
        for note in page_obj.object_list:
            icon, tone = _notification_style(note.event_type)
            rows.append(
                NotificationRow(
                    id=str(note.pk),
                    title=note.title,
                    body=note.body,
                    is_read=note.is_read,
                    created_at=self._relative_time(note.created_at),
                    icon=icon,
                    tone=tone,
                    mark_read_url=pu(
                        "professor_notification_read", notification_id=note.pk
                    ),
                )
            )

        return NotificationsPageContext(
            notifications=rows,
            unread_count=unread,
            page=page_obj.number,
            total_pages=paginator.num_pages,
            total_count=paginator.count,
        )

    def list_messages(
        self, user: ProfessorUser, *, page: int = 1
    ) -> NotificationsPageContext:
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        qs = (
            Notification.objects.filter(
                recipient_domain="professor", recipient_id=user.pk
            )
            .filter(event_type__icontains="message")
            .order_by("-created_at")
        )
        unread = qs.filter(is_read=False).count()
        paginator = Paginator(qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)
        rows = [
            NotificationRow(
                id=str(note.pk),
                title=note.title,
                body=note.body,
                is_read=note.is_read,
                created_at=self._relative_time(note.created_at),
                icon="bi-chat",
                tone="info",
                mark_read_url=pu(
                    "professor_notification_read", notification_id=note.pk
                ),
            )
            for note in page_obj.object_list
        ]
        return NotificationsPageContext(
            notifications=rows,
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
