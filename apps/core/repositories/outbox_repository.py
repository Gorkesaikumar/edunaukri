from apps.core.models.outbox_event import OutboxEvent
from apps.core.repositories.crud import CRUDRepository


class OutboxEventRepository(CRUDRepository):
    model = OutboxEvent
