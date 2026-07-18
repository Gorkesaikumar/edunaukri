from django.db import transaction
from django.utils import timezone

from apps.core.models.outbox_event import OutboxEvent, OutboxEventStatus
from apps.core.repositories.outbox_repository import OutboxEventRepository
from apps.core.selectors.outbox_selector import OutboxEventSelector
from apps.core.services.base import BaseService


class OutboxService(BaseService):
    def __init__(self):
        self.repository = OutboxEventRepository()
        self.selector = OutboxEventSelector()

    @transaction.atomic
    def publish(
        self,
        *,
        domain: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id,
        payload: dict | None = None,
    ) -> OutboxEvent:
        return self.repository.create(
            domain=domain,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload or {},
        )

    @transaction.atomic
    def mark_processing(self, event: OutboxEvent) -> OutboxEvent:
        return self.repository.update(event, status=OutboxEventStatus.PROCESSING)

    @transaction.atomic
    def mark_completed(self, event: OutboxEvent) -> OutboxEvent:
        return self.repository.update(
            event,
            status=OutboxEventStatus.COMPLETED,
            processed_at=timezone.now(),
        )

    @transaction.atomic
    def mark_failed(self, event: OutboxEvent, error_message: str) -> OutboxEvent:
        return self.repository.update(
            event,
            status=OutboxEventStatus.FAILED,
            retry_count=event.retry_count + 1,
            error_message=error_message[:2000],
        )

    def fetch_pending(self, limit: int = 50):
        return self.selector.fetch_pending(limit=limit)
