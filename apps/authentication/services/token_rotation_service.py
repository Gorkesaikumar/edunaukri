"""Enterprise token rotation with session synchronization and reuse detection."""

from __future__ import annotations

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.repositories.user_repository import get_user_repository
from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.validators.account_validator import (
    get_account_access_block_reason,
)
from apps.core.services.base import BaseService


class TokenRotationService(BaseService):
    """Rotate JWT refresh tokens while preserving session identity."""

    def __init__(self):
        self.sessions = SessionManagementService()
        self.audit = AuthAuditService()

    def refresh_tokens(
        self,
        *,
        refresh_token: str,
        request_meta: dict | None = None,
    ) -> tuple[str, str | None]:
        meta = request_meta or {}
        try:
            refresh = RefreshToken(refresh_token)
        except TokenError as exc:
            raise ValueError("Invalid or expired refresh token.") from exc

        domain = refresh.get("domain")
        user_id = refresh.get("user_id")
        session_uuid = refresh.get("session_uuid")
        old_jti = refresh.get("jti")

        if not domain or not user_id:
            raise ValueError("Invalid token claims.")

        if self._is_blacklisted(old_jti):
            self._handle_reuse(
                domain=domain,
                user_id=user_id,
                session_uuid=session_uuid,
                request_meta=meta,
            )
            raise ValueError("Refresh token has been revoked.")

        user = get_user_repository(domain).get_by_id(user_id)
        if user is None or get_account_access_block_reason(user) is not None:
            raise ValueError("User account is not active.")

        access = str(refresh.access_token)
        rotated: str | None = None

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            try:
                refresh.outstand()
            except AttributeError:
                pass
            new_jti = refresh.get("jti")
            rotated = str(refresh)
            if old_jti and new_jti:
                self.sessions.rotate_session_key(
                    old_session_key=str(old_jti),
                    new_session_key=str(new_jti),
                    session_uuid=str(session_uuid) if session_uuid else None,
                )
        elif old_jti:
            self.sessions.touch_session(str(old_jti))

        self.audit.record_token_refresh(
            domain=domain,
            user_id=user_id,
            session_uuid=str(session_uuid) if session_uuid else None,
            request_meta=meta,
        )
        return access, rotated

    def _handle_reuse(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None,
        request_meta: dict | None,
    ) -> None:
        self.audit.record_token_reuse_detected(
            domain=domain,
            user_id=user_id,
            session_uuid=str(session_uuid) if session_uuid else None,
            request_meta=request_meta,
        )
        if session_uuid:
            self.sessions.revoke_by_session_key(
                "",
                session_uuid=session_uuid,
                domain=domain,
                user_id=user_id,
                request_meta=request_meta,
                audit=False,
            )
        self.sessions.revoke_all_for_user(
            domain=domain,
            user_id=user_id,
            request_meta=request_meta,
            audit=False,
        )

    @staticmethod
    def _is_blacklisted(jti: str | None) -> bool:
        if not jti:
            return False
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )

            outstanding = OutstandingToken.objects.filter(jti=jti).first()
            return bool(
                outstanding
                and BlacklistedToken.objects.filter(token=outstanding).exists()
            )
        except Exception:
            return False
