"""Recruiter notifications portal context."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.notifications.models import Notification


@dataclass
class RecruiterNotificationsPortalContext:
    notifications: list[dict]
    unread_count: int
    mark_all_url: str


class RecruiterNotificationsPortalService(BaseService):
    def build(self, profile: RecruiterProfile) -> RecruiterNotificationsPortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        qs = Notification.objects.filter(
            recipient_domain="it", recipient_id=user.pk, is_deleted=False
        ).order_by("-created_at")
        unread = qs.filter(is_read=False).count()
        rows = qs[:50]
        items = []
        for row in rows:
            items.append(
                {
                    "id": str(row.pk),
                    "title": row.title,
                    "body": row.body,
                    "is_read": row.is_read,
                    "occurred_label": timezone.localtime(row.created_at).strftime(
                        "%b %d, %Y · %I:%M %p"
                    ),
                    "mark_read_url": pu(
                        "recruiter_notification_read", notification_id=row.pk
                    ),
                }
            )
        return RecruiterNotificationsPortalContext(
            notifications=items,
            unread_count=unread,
            mark_all_url=pu("recruiter_notifications_mark_all_read"),
        )
