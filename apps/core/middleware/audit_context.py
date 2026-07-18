import hashlib
import json
import threading
from dataclasses import dataclass

_actor_context = threading.local()


@dataclass
class AuditActor:
    actor_type: str
    actor_id: str | None = None


def set_audit_actor(actor: AuditActor | None) -> None:
    _actor_context.actor = actor


def get_audit_actor() -> AuditActor | None:
    return getattr(_actor_context, "actor", None)


class AuditContextMiddleware:
    """Attach audit actor from authenticated user to thread-local context."""

    ACTOR_TYPE_MAP = {
        "AdminUser": "admin",
        "ITUser": "it_user",
        "ProfessorUser": "professor",
        "CollegeUser": "college",
        "FacultyUser": "professor",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            model_name = user.__class__.__name__
            set_audit_actor(
                AuditActor(
                    actor_type=self.ACTOR_TYPE_MAP.get(model_name, "system"),
                    actor_id=str(user.pk),
                )
            )
        else:
            set_audit_actor(None)

        response = self.get_response(request)
        set_audit_actor(None)
        return response
