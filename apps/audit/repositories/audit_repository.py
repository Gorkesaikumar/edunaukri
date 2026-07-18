from apps.audit.models import AuditEvent
from apps.core.repositories.crud import CRUDRepository


class AuditEventRepository(CRUDRepository):
    model = AuditEvent
