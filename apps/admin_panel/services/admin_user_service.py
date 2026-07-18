from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.repositories.user_repository import get_user_repository
from apps.admin_panel.selectors.audit_selector import AuditSelector
from apps.admin_panel.services.admin_audit import record_admin_action
from apps.admin_panel.selectors.user_selector import UserSelector
from apps.authentication.models import LoginAttempt
from apps.authentication.services.session_revocation_service import (
    SessionRevocationService,
)
from apps.authentication.services.user_activation_service import UserActivationService
from apps.authentication.validators.password_validator import validate_password_strength
from apps.core.services.base import BaseService


class AdminUserService(BaseService):
    def __init__(self):
        self.selector = UserSelector()
        self.activation = UserActivationService()
        self.sessions = SessionRevocationService()

    def list_users(self, **filters):
        return self.selector.list_users(**filters)

    def get_user(self, *, domain: str, user_id):
        return self.selector.get_user(domain=domain, user_id=user_id)

    @transaction.atomic
    def activate(self, *, domain: str, user_id, admin_id) -> None:
        self.activation.activate(domain=domain, user_id=user_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.user.activated",
            entity_type=f"{domain}_user",
            entity_id=user_id,
        )

    @transaction.atomic
    def suspend(self, *, domain: str, user_id, admin_id) -> None:
        self.activation.suspend(domain=domain, user_id=user_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.user.suspended",
            entity_type=f"{domain}_user",
            entity_id=user_id,
        )

    @transaction.atomic
    def deactivate(self, *, domain: str, user_id, admin_id) -> None:
        self.activation.deactivate(domain=domain, user_id=user_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.user.deactivated",
            entity_type=f"{domain}_user",
            entity_id=user_id,
        )

    @transaction.atomic
    def lifecycle_action(self, *, domain: str, user_id, action: str, admin_id) -> None:
        actions = {
            "activate": self.activate,
            "suspend": self.suspend,
            "deactivate": self.deactivate,
        }
        handler = actions.get(action)
        if not handler:
            raise ValidationError("Invalid lifecycle action.")
        handler(domain=domain, user_id=user_id, admin_id=admin_id)

    @transaction.atomic
    def verify_user(self, *, domain: str, user_id, admin_id) -> None:
        user = get_user_repository(domain).get_by_id(user_id)
        if not user:
            raise ValidationError("User not found.")
        update_fields = ["updated_at"]
        if hasattr(user, "email_verified"):
            user.email_verified = True
            update_fields.append("email_verified")
        if (
            hasattr(user, "account_status")
            and user.account_status == AccountStatus.PENDING_VERIFICATION
        ):
            user.account_status = AccountStatus.ACTIVE
            update_fields.append("account_status")
        user.is_active = True
        update_fields.append("is_active")
        user.save(update_fields=list(dict.fromkeys(update_fields)))
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.user.verified",
            entity_type=f"{domain}_user",
            entity_id=user_id,
        )

    @transaction.atomic
    def reset_password(
        self, *, domain: str, user_id, new_password: str, admin_id
    ) -> None:
        user = get_user_repository(domain).get_by_id(user_id)
        if not user:
            raise ValidationError("User not found.")
        validate_password_strength(new_password)
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        self.sessions.revoke_sessions(domain=domain, user_id=user_id, admin_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.user.password_reset",
            entity_type=f"{domain}_user",
            entity_id=user_id,
        )

    @transaction.atomic
    def force_logout(self, *, domain: str, user_id, admin_id) -> None:
        if not get_user_repository(domain).get_by_id(user_id):
            raise ValidationError("User not found.")
        self.sessions.revoke_sessions(domain=domain, user_id=user_id, admin_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.user.force_logout",
            entity_type=f"{domain}_user",
            entity_id=user_id,
        )

    def login_history(self, *, domain: str, user_id, limit: int = 50) -> list[dict]:
        attempts = LoginAttempt.objects.filter(domain=domain, user_id=user_id).order_by(
            "-attempted_at"
        )[:limit]
        return [
            {
                "id": str(a.pk),
                "email": a.email,
                "result": a.result,
                "ip_address": a.ip_address,
                "user_agent": a.user_agent,
                "failure_reason": a.failure_reason,
                "attempted_at": a.attempted_at.isoformat(),
            }
            for a in attempts
        ]

    def user_activity(self, *, domain: str, user_id, limit: int = 50) -> list[dict]:
        events = (
            AuditSelector().search(actor_id=user_id).order_by("-occurred_at")[:limit]
        )
        return [
            {
                "id": str(e.pk),
                "domain": e.domain,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": str(e.entity_id) if e.entity_id else None,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]

    def user_exists(self, domain: str, user_id) -> bool:
        return get_user_repository(domain).get_by_id(user_id) is not None
