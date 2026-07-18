from apps.core.repositories.crud import CRUDRepository
from apps.notifications.models import Notification


class NotificationRepository(CRUDRepository):
    model = Notification
