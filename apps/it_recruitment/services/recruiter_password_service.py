"""Secure password change for recruiter settings portal."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.validators.enterprise_password import (
    validate_enterprise_password,
)
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.recruiter_account_settings_service import (
    RecruiterAccountSettingsService,
)


class RecruiterPasswordService(BaseService):
    def __init__(self):
        self.audit = AuthAuditService()
        self.sessions = SessionManagementService()
        self.settings = RecruiterAccountSettingsService()

    @BaseService.atomic
    def change_password(
        self,
        profile: RecruiterProfile,
        *,
        current_password: str,
        new_password: str,
        confirm_password: str,
        request,
    ) -> dict:
        current_password = (current_password or "").strip()
        new_password = new_password or ""
        confirm_password = confirm_password or ""

        if not current_password:
            raise ValidationException("Current password is required.")
        if not new_password:
            raise ValidationException("New password is required.")
        if not confirm_password:
            raise ValidationException("Please confirm your new password.")
        if new_password != confirm_password:
            raise ValidationException("New password and confirmation do not match.")
        if new_password == current_password:
            raise ValidationException(
                "New password must be different from your current password."
            )

        user = profile.user
        if not user.check_password(current_password):
            raise ValidationException("Current password is incorrect.")
        try:
            validate_enterprise_password(new_password, user=user)
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise ValidationException(message) from exc

        user.set_password(new_password)
        user.reset_login_attempts()
        user.save(
            update_fields=[
                "password",
                "failed_login_attempts",
                "locked_until",
                "updated_at",
            ]
        )

        prefs = self.settings.get_or_create_settings(profile)
        prefs.password_changed_at = timezone.now()
        prefs.save(update_fields=["password_changed_at", "updated_at"])

        current_key = self.sessions.current_session_key_from_request(request)
        meta = self._meta(request)
        revoked = self.sessions.revoke_other_sessions(
            domain=DomainType.IT,
            user_id=user.pk,
            current_session_key=current_key,
            request_meta=meta,
        )

        self.audit.record_password_changed(
            domain=DomainType.IT,
            user_id=user.pk,
            sessions_revoked=revoked,
            request_meta=meta,
        )

        changed_label = timezone.localtime(prefs.password_changed_at).strftime(
            "%b %d, %Y"
        )
        return {
            "password_changed_label": changed_label,
            "sessions_revoked": revoked,
        }

    @staticmethod
    def _meta(request) -> dict:
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
