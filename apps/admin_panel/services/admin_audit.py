from apps.audit.services.audit_service import AuditService
from apps.core.constants.enums import DomainType


def record_admin_action(
    *,
    admin_id,
    event_type: str,
    entity_type: str = "",
    entity_id=None,
    payload: dict | None = None,
) -> None:
    AuditService().record(
        domain=DomainType.PLATFORM,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload={"admin_id": str(admin_id), **(payload or {})},
        actor_type="admin",
        actor_id=admin_id,
    )
