from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.validators.password_validator import validate_password_strength
from apps.core.services.base import BaseService


class PasswordChangeService(BaseService):
    def __init__(self):
        self.sessions = SessionManagementService()
        self.audit = AuthAuditService()

    @transaction.atomic
    def change_password(
        self,
        *,
        user,
        current_password: str,
        new_password: str,
        request=None,
    ) -> dict:
        if not user.check_password(current_password):
            raise ValidationError("Current password is incorrect.")
        validate_password_strength(new_password, user=user)
        user.set_password(new_password)
        if hasattr(user, "reset_login_attempts"):
            user.reset_login_attempts()
        user.save(
            update_fields=["password", "updated_at"]
            + (
                ["failed_login_attempts", "locked_until"]
                if hasattr(user, "failed_login_attempts")
                else []
            )
        )

        domain = getattr(user, "domain", None)
        meta = self._meta(request)
        revoked = 0
        if domain:
            current_key = (
                self.sessions.current_session_key_from_request(request)
                if request
                else None
            )
            revoked = self.sessions.revoke_other_sessions(
                domain=domain,
                user_id=user.pk,
                current_session_key=current_key,
                request_meta=meta,
            )
            self.audit.record_password_changed(
                domain=domain,
                user_id=user.pk,
                sessions_revoked=revoked,
                request_meta=meta,
            )

        return {
            "sessions_revoked": revoked,
            "password_changed_at": timezone.now().isoformat(),
        }

    @staticmethod
    def _meta(request) -> dict:
        if not request:
            return {}
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
