import hashlib
import json

from apps.audit.models import AuditEvent
from apps.audit.repositories.audit_repository import AuditEventRepository
from apps.core.constants.enums import ActorType
from apps.core.middleware.audit_context import get_audit_actor


class AuditService:
    """Append-only audit logging service."""

    def __init__(self, repository=None):
        self.repository = repository or AuditEventRepository()

    def record(
        self,
        *,
        domain: str,
        event_type: str,
        entity_type: str = "",
        entity_id=None,
        payload: dict | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
        request_id: str = "",
        actor_type: str | None = None,
        actor_id=None,
    ) -> AuditEvent:
        actor = get_audit_actor()
        resolved_actor_type = actor_type or (
            actor.actor_type if actor else ActorType.SYSTEM
        )
        resolved_actor_id = actor_id or (actor.actor_id if actor else None)

        payload = payload or {}
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        return self.repository.create(
            domain=domain,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=resolved_actor_type,
            actor_id=resolved_actor_id,
            ip_address=ip_address,
            user_agent=user_agent[:500],
            request_id=request_id,
            payload_hash=payload_hash,
            payload=payload,
        )
