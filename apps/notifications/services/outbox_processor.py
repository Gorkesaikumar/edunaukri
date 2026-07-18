import logging

from django.db import transaction

from apps.authentication.constants.events import AUTH_EMAIL_EVENT_TYPES
from apps.authentication.services.email_delivery_service import AuthEmailDeliveryService
from apps.billing.constants.events import BILLING_PLACEMENT_EVENT_TYPES
from apps.billing.services.placement_billing_service import PlacementBillingService
from apps.core.models.outbox_event import OutboxEvent
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.notifications.constants.enums import NotificationChannel, NotificationStatus
from apps.notifications.repositories.notification_repository import (
    NotificationRepository,
)

logger = logging.getLogger(__name__)

EVENT_TITLES = {
    "application.placed": "Application placed",
    "application.submitted": "New application received",
    "application.status_changed": "Application status updated",
    "interview.scheduled": "Interview scheduled",
    "interview.rescheduled": "Interview rescheduled",
    "interview.meeting_link_updated": "Meeting link updated",
    "interview.instructions_updated": "Interview instructions updated",
    "interview.cancelled": "Interview cancelled",
    "interview.confirmed": "Candidate confirmed interview",
    "interview.reschedule_requested": "Reschedule requested",
    "interview.feedback_available": "Interview feedback available",
    "interview.reminder": "Interview reminder",
    "resume.uploaded": "Resume uploaded",
    "resume.updated": "Resume updated",
    "resume.deleted": "Resume deleted",
    "resume.match_improved": "Resume match improved",
    "resume.viewed": "Resume viewed",
    "resume_downloaded": "Resume downloaded",
    "invoice.issued": "Invoice issued",
    "claim.submitted": "Guarantee claim submitted",
    "job.recommended": "New job matches",
}


class NotificationDispatcher(BaseService):
    """Phase 1 dispatcher — creates in-app notifications; email via auth delivery service."""

    def __init__(self):
        self.auth_email = AuthEmailDeliveryService()
        self.notification_repository = NotificationRepository()

    @transaction.atomic
    def dispatch(self, event: OutboxEvent):
        if event.event_type in AUTH_EMAIL_EVENT_TYPES:
            self.auth_email.deliver(event)
            return None

        payload = event.payload or {}
        recipient_domain = payload.get("recipient_domain")
        recipient_id = payload.get("recipient_id")
        if not recipient_domain or not recipient_id:
            logger.warning("Outbox event %s missing recipient metadata", event.pk)
            return None

        title = payload.get("title") or EVENT_TITLES.get(
            event.event_type, event.event_type
        )
        body = payload.get("body", "")

        notification = self.notification_repository.create(
            recipient_domain=recipient_domain,
            recipient_id=recipient_id,
            channel=NotificationChannel.IN_APP,
            title=title,
            body=body,
            event_type=event.event_type,
            entity_type=event.aggregate_type,
            entity_id=event.aggregate_id,
            status=NotificationStatus.DELIVERED,
            payload=payload,
        )

        if payload.get("send_email"):
            logger.info(
                "Email stub: would send '%s' to %s/%s",
                title,
                recipient_domain,
                recipient_id,
            )

        return notification


class OutboxProcessorService(BaseService):
    def __init__(self):
        self.outbox = OutboxService()
        self.dispatcher = NotificationDispatcher()
        self.billing = PlacementBillingService()

    def process_batch(self, limit: int = 50) -> int:
        processed = 0
        for event in self.outbox.fetch_pending(limit=limit):
            self.outbox.mark_processing(event)
            try:
                if event.event_type in BILLING_PLACEMENT_EVENT_TYPES:
                    self.billing.handle_outbox_event(event)
                self.dispatcher.dispatch(event)
                self.outbox.mark_completed(event)
                processed += 1
            except Exception as exc:
                self.outbox.mark_failed(event, str(exc))
        return processed
