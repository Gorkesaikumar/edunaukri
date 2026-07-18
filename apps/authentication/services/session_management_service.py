"""Login session registration and revocation."""

from __future__ import annotations

import uuid

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import UserLoginSession
from apps.authentication.utils.user_agent import parse_user_agent
from apps.core.services.base import BaseService


class SessionManagementService(BaseService):
    def register_session(
        self,
        *,
        domain: str,
        user_id,
        refresh_token: str,
        request_meta: dict | None = None,
        session_uuid=None,
        auth_method: str = "password",
    ) -> UserLoginSession:
        meta = request_meta or {}
        ua_info = parse_user_agent(meta.get("user_agent", ""))
        session_key = self._session_key_from_refresh(refresh_token)
        session_uuid = session_uuid or uuid.uuid4()
        ip = meta.get("ip_address")
        is_new_device = self._is_new_device(
            domain=domain, user_id=user_id, ua_info=ua_info
        )

        session = UserLoginSession.objects.create(
            domain=domain,
            user_id=user_id,
            session_uuid=session_uuid,
            session_key=session_key,
            device_label=ua_info["device_label"],
            browser=ua_info["browser"],
            os_name=ua_info["os_name"],
            ip_address=ip,
            location_label=self._location_label(ip),
            login_at=timezone.now(),
            last_active_at=timezone.now(),
        )

        from apps.authentication.services.auth_audit_service import AuthAuditService

        audit = AuthAuditService()
        audit.record_login_success(
            domain=domain,
            user_id=user_id,
            session_uuid=str(session_uuid),
            request_meta=meta,
            method=auth_method,
        )
        if is_new_device:
            audit.record_new_device_login(
                domain=domain,
                user_id=user_id,
                session_uuid=str(session_uuid),
                request_meta=meta,
            )
        return session

    def rotate_session_key(
        self,
        *,
        old_session_key: str,
        new_session_key: str,
        session_uuid: str | None = None,
    ) -> None:
        qs = UserLoginSession.objects.filter(
            session_key=old_session_key, revoked_at__isnull=True
        )
        if session_uuid:
            qs = qs.filter(session_uuid=session_uuid)
        qs.update(session_key=new_session_key, last_active_at=timezone.now())

    def touch_session(self, session_key: str) -> None:
        UserLoginSession.objects.filter(
            session_key=session_key, revoked_at__isnull=True
        ).update(last_active_at=timezone.now())

    def revoke_by_refresh_token(
        self,
        refresh_token: str,
        *,
        request_meta: dict | None = None,
    ) -> UserLoginSession | None:
        try:
            token = RefreshToken(refresh_token)
        except Exception:
            return None
        session_key = str(token.get("jti") or "")
        session_uuid = token.get("session_uuid")
        domain = token.get("domain")
        user_id = token.get("user_id")
        session = self.revoke_by_session_key(
            session_key,
            session_uuid=session_uuid,
            domain=domain,
            user_id=user_id,
            request_meta=request_meta,
        )
        return session

    def revoke_by_session_key(
        self,
        session_key: str,
        *,
        session_uuid: str | None = None,
        domain: str | None = None,
        user_id=None,
        request_meta: dict | None = None,
        audit: bool = True,
    ) -> UserLoginSession | None:
        qs = UserLoginSession.objects.filter(revoked_at__isnull=True)
        if session_key:
            qs = qs.filter(session_key=session_key)
        elif session_uuid:
            qs = qs.filter(session_uuid=session_uuid)
        else:
            return None
        if session_uuid and session_key:
            qs = qs.filter(session_uuid=session_uuid)
        session = qs.first()
        if not session:
            return None
        self._blacklist_session_key(session.session_key)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])
        if audit:
            from apps.authentication.services.auth_audit_service import AuthAuditService

            AuthAuditService().record_session_revoked(
                domain=domain or session.domain,
                user_id=user_id or session.user_id,
                session_uuid=str(session.session_uuid),
                request_meta=request_meta,
            )
        return session

    def revoke_all_for_user(
        self,
        *,
        domain: str,
        user_id,
        exclude_session_key: str | None = None,
        request_meta: dict | None = None,
        audit: bool = True,
    ) -> int:
        qs = UserLoginSession.objects.filter(
            domain=domain, user_id=user_id, is_deleted=False, revoked_at__isnull=True
        )
        if exclude_session_key:
            qs = qs.exclude(session_key=exclude_session_key)
        count = 0
        for session in qs:
            self._blacklist_session_key(session.session_key)
            session.revoked_at = timezone.now()
            session.save(update_fields=["revoked_at", "updated_at"])
            count += 1
        if audit and count:
            from apps.authentication.services.auth_audit_service import AuthAuditService

            AuthAuditService().record_logout_all_devices(
                domain=domain,
                user_id=user_id,
                count=count,
                request_meta=request_meta,
            )
        return count

    def list_sessions(
        self, *, domain: str, user_id, current_session_key: str | None = None
    ) -> list[dict]:
        rows = UserLoginSession.objects.filter(
            domain=domain, user_id=user_id, is_deleted=False, revoked_at__isnull=True
        ).order_by("-last_active_at")
        return [self._serialize(row, current_session_key) for row in rows]

    @BaseService.atomic
    def revoke_session(
        self,
        *,
        domain: str,
        user_id,
        session_id,
        current_session_key: str | None = None,
    ) -> None:
        session = UserLoginSession.objects.filter(
            pk=session_id,
            domain=domain,
            user_id=user_id,
            is_deleted=False,
            revoked_at__isnull=True,
        ).first()
        if not session:
            from apps.core.exceptions.domain_exceptions import ResourceNotFoundException

            raise ResourceNotFoundException("Session not found.")
        if current_session_key and session.session_key == current_session_key:
            from apps.core.exceptions.domain_exceptions import ValidationException

            raise ValidationException(
                "Cannot revoke your current session from this screen."
            )
        self.revoke_by_session_key(
            session.session_key,
            session_uuid=str(session.session_uuid),
            domain=domain,
            user_id=user_id,
            audit=True,
        )

    @BaseService.atomic
    def revoke_other_sessions(
        self,
        *,
        domain: str,
        user_id,
        current_session_key: str | None = None,
        request_meta: dict | None = None,
    ) -> int:
        return self.revoke_all_for_user(
            domain=domain,
            user_id=user_id,
            exclude_session_key=current_session_key,
            request_meta=request_meta,
            audit=True,
        )

    def current_session_key_from_request(self, request) -> str | None:
        from apps.authentication.services.web_jwt_service import WebJWTService

        refresh = request.COOKIES.get(WebJWTService().refresh_cookie)
        if not refresh:
            return None
        try:
            return self._session_key_from_refresh(refresh)
        except Exception:
            return None

    def current_session_uuid_from_request(self, request) -> str | None:
        from apps.authentication.services.web_jwt_service import WebJWTService

        refresh = request.COOKIES.get(WebJWTService().refresh_cookie)
        if not refresh:
            return None
        try:
            token = RefreshToken(refresh)
            value = token.get("session_uuid")
            return str(value) if value else None
        except Exception:
            return None

    @staticmethod
    def _session_key_from_refresh(refresh_token: str) -> str:
        token = RefreshToken(refresh_token)
        jti = token.get("jti")
        if not jti:
            raise ValueError("Refresh token missing jti.")
        return str(jti)

    @staticmethod
    def _blacklist_session_key(session_key: str) -> None:
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )

            outstanding = OutstandingToken.objects.filter(jti=session_key).first()
            if (
                outstanding
                and not BlacklistedToken.objects.filter(token=outstanding).exists()
            ):
                BlacklistedToken.objects.create(token=outstanding)
        except Exception:
            pass

    def blacklist_all_tokens_for_user(self, *, domain: str, user_id) -> int:
        """Blacklist every outstanding refresh token issued for a domain user."""
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
        from rest_framework_simplejwt.tokens import UntypedToken

        user_id_str = str(user_id)
        count = 0
        for outstanding in OutstandingToken.objects.only(
            "id", "token", "jti"
        ).iterator():
            try:
                payload = UntypedToken(outstanding.token)
                if payload.get("domain") != domain:
                    continue
                if str(payload.get("user_id")) != user_id_str:
                    continue
                if BlacklistedToken.objects.filter(token=outstanding).exists():
                    continue
                BlacklistedToken.objects.create(token=outstanding)
                count += 1
            except Exception:
                continue
        return count

    def force_revoke_all_for_user(
        self,
        *,
        domain: str,
        user_id,
        request_meta: dict | None = None,
    ) -> dict:
        """Admin or security action — terminate every session and blacklist all refresh tokens."""
        blacklisted = self.blacklist_all_tokens_for_user(domain=domain, user_id=user_id)
        sessions_revoked = self.revoke_all_for_user(
            domain=domain,
            user_id=user_id,
            request_meta=request_meta,
            audit=True,
        )
        return {"sessions_revoked": sessions_revoked, "tokens_blacklisted": blacklisted}

    @staticmethod
    def _is_new_device(*, domain: str, user_id, ua_info: dict) -> bool:
        return not UserLoginSession.objects.filter(
            domain=domain,
            user_id=user_id,
            browser=ua_info["browser"],
            os_name=ua_info["os_name"],
            device_label=ua_info["device_label"],
        ).exists()

    @staticmethod
    def _location_label(ip: str | None) -> str:
        if not ip:
            return "Unknown location"
        if ip.startswith("127.") or ip == "::1":
            return "Local network"
        return "Approximate location unavailable"

    @staticmethod
    def _serialize(session: UserLoginSession, current_session_key: str | None) -> dict:
        return {
            "id": str(session.id),
            "session_uuid": str(session.session_uuid),
            "device_label": session.device_label or "Unknown device",
            "browser": session.browser,
            "os_name": session.os_name,
            "ip_address": session.ip_address or "—",
            "location_label": session.location_label or "—",
            "login_at": session.login_at.isoformat(),
            "login_label": timezone.localtime(session.login_at).strftime(
                "%b %d, %Y · %I:%M %p"
            ),
            "last_active_label": timezone.localtime(session.last_active_at).strftime(
                "%b %d, %Y · %I:%M %p"
            ),
            "is_current": bool(
                current_session_key and session.session_key == current_session_key
            ),
        }
