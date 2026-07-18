"""Enterprise authentication audit logging."""

from __future__ import annotations

from apps.authentication.constants.auth_events import (
    AUTH_LOGIN_FAILURE,
    AUTH_LOGIN_SUCCESS,
    AUTH_LOGOUT,
    AUTH_LOGOUT_ALL_DEVICES,
    AUTH_NEW_DEVICE_LOGIN,
    AUTH_PASSWORD_CHANGED,
    AUTH_SESSION_REVOKED,
    AUTH_TOKEN_REFRESH,
    AUTH_TOKEN_REUSE_DETECTED,
    AUTH_UNAUTHORIZED_UUID_ACCESS,
)
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.utils.user_agent import parse_user_agent
from apps.core.services.base import BaseService


class AuthAuditService(BaseService):
    """Record authentication and session lifecycle events."""

    def __init__(self):
        self._audit = SecurityAuditService()

    def record_login_success(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None = None,
        request_meta: dict | None = None,
        method: str = "password",
    ) -> None:
        meta = request_meta or {}
        ua = parse_user_agent(meta.get("user_agent", ""))
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_LOGIN_SUCCESS,
            title="Signed in successfully",
            description=f"Signed in via {method} from {ua['device_label']}.",
            ip_address=meta.get("ip_address"),
            metadata={
                "session_uuid": session_uuid,
                "method": method,
                "browser": ua["browser"],
                "os_name": ua["os_name"],
                "device_label": ua["device_label"],
                "user_agent": meta.get("user_agent", "")[:500],
            },
        )

    def record_login_failure(
        self,
        *,
        domain: str,
        email: str,
        user_id=None,
        reason: str = "",
        request_meta: dict | None = None,
    ) -> None:
        if not user_id:
            return
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_LOGIN_FAILURE,
            title="Failed sign-in attempt",
            description=f"Failed sign-in for {email}. Reason: {reason or 'invalid_credentials'}.",
            ip_address=meta.get("ip_address"),
            metadata={
                "email": email,
                "reason": reason,
                "user_agent": meta.get("user_agent", "")[:500],
            },
        )

    def record_new_device_login(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None = None,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        ua = parse_user_agent(meta.get("user_agent", ""))
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_NEW_DEVICE_LOGIN,
            title="New device sign-in",
            description=f"Your account was accessed from a new device: {ua['device_label']}.",
            ip_address=meta.get("ip_address"),
            metadata={
                "session_uuid": session_uuid,
                "browser": ua["browser"],
                "os_name": ua["os_name"],
                "device_label": ua["device_label"],
            },
        )

    def record_logout(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None = None,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_LOGOUT,
            title="Signed out",
            description="You signed out of your account.",
            ip_address=meta.get("ip_address"),
            metadata={
                "session_uuid": session_uuid,
                "user_agent": meta.get("user_agent", "")[:500],
            },
        )

    def record_token_refresh(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None = None,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_TOKEN_REFRESH,
            title="Session refreshed",
            description="Your authentication session was refreshed.",
            ip_address=meta.get("ip_address"),
            metadata={
                "session_uuid": session_uuid,
                "user_agent": meta.get("user_agent", "")[:500],
            },
        )

    def record_token_reuse_detected(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None = None,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_TOKEN_REUSE_DETECTED,
            title="Suspicious token reuse detected",
            description="A revoked refresh token was reused. Related sessions were terminated.",
            ip_address=meta.get("ip_address"),
            metadata={
                "session_uuid": session_uuid,
                "user_agent": meta.get("user_agent", "")[:500],
            },
        )

    def record_logout_all_devices(
        self,
        *,
        domain: str,
        user_id,
        count: int,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_LOGOUT_ALL_DEVICES,
            title="Signed out of other devices",
            description=f"{count} other session(s) were signed out.",
            ip_address=meta.get("ip_address"),
            metadata={"sessions_revoked": count},
        )

    def record_session_revoked(
        self,
        *,
        domain: str,
        user_id,
        session_uuid: str | None = None,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_SESSION_REVOKED,
            title="Session revoked",
            description="An active login session was revoked.",
            ip_address=meta.get("ip_address"),
            metadata={"session_uuid": session_uuid},
        )

    def record_password_changed(
        self,
        *,
        domain: str,
        user_id,
        sessions_revoked: int = 0,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_PASSWORD_CHANGED,
            title="Password changed",
            description=f"Your password was updated. {sessions_revoked} other session(s) were signed out.",
            ip_address=meta.get("ip_address"),
            metadata={"sessions_revoked": sessions_revoked},
        )

    def record_oauth_connected(
        self,
        *,
        domain: str,
        user_id,
        provider: str,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type="auth.oauth.connected",
            title=f"{provider.title()} account connected",
            description=f"Your {provider.title()} account was linked successfully.",
            ip_address=meta.get("ip_address"),
            metadata={"provider": provider},
        )

    def record_oauth_disconnected(
        self,
        *,
        domain: str,
        user_id,
        provider: str,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        self._record(
            domain=domain,
            user_id=user_id,
            event_type="auth.oauth.disconnected",
            title=f"{provider.title()} account disconnected",
            description=f"Your {provider.title()} account was unlinked.",
            ip_address=meta.get("ip_address"),
            metadata={"provider": provider},
        )

    def record_unauthorized_uuid_access(
        self,
        *,
        domain: str,
        user_id,
        authenticated_uuid: str,
        requested_uuid: str,
        requested_path: str,
        portal: str,
        request_meta: dict | None = None,
    ) -> None:
        meta = request_meta or {}
        ua_label = meta.get("device_label") or "Unknown device"
        self._record(
            domain=domain,
            user_id=user_id,
            event_type=AUTH_UNAUTHORIZED_UUID_ACCESS,
            title="Unauthorized portal access blocked",
            description=(
                f"Attempted to access {portal} portal UUID {requested_uuid} "
                f"while authenticated as {authenticated_uuid}."
            ),
            ip_address=meta.get("ip_address"),
            metadata={
                "authenticated_uuid": authenticated_uuid,
                "requested_uuid": requested_uuid,
                "requested_path": requested_path,
                "portal": portal,
                "browser": meta.get("browser", ""),
                "os_name": meta.get("os_name", ""),
                "device_label": ua_label,
                "user_agent": meta.get("user_agent", "")[:500],
            },
        )

    def _record(self, **kwargs) -> None:
        metadata = kwargs.pop("metadata", {}) or {}
        session_uuid = metadata.get("session_uuid")
        if session_uuid:
            metadata["session_uuid"] = str(session_uuid)
        metadata.setdefault("user_uuid", str(kwargs.get("user_id")))
        self._audit.record(metadata=metadata, **kwargs)
