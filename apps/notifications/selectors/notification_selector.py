from apps.core.selectors.read import ReadSelector
from apps.notifications.models import Notification


class NotificationSelector(ReadSelector):
    model = Notification

    def for_recipient(self, domain: str, recipient_id, *, unread_only: bool = False):
        queryset = self.filter_by(recipient_domain=domain, recipient_id=recipient_id)
        if unread_only:
            queryset = queryset.filter(is_read=False)
        return queryset.order_by("-created_at")

    def get_for_recipient(self, notification_id, domain: str, recipient_id):
        return self.filter_by(
            pk=notification_id,
            recipient_domain=domain,
            recipient_id=recipient_id,
        ).first()
