from apps.core.models.outbox_event import OutboxEvent, OutboxEventStatus
from apps.core.selectors.read import ReadSelector


class OutboxEventSelector(ReadSelector):
    model = OutboxEvent

    def fetch_pending(self, limit: int = 50):
        return self.filter_by(status=OutboxEventStatus.PENDING).order_by("created_at")[
            :limit
        ]
