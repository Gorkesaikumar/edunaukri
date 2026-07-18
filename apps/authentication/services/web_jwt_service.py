"""HttpOnly JWT cookie management for server-rendered web authentication."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.http import HttpResponseBase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.serializers.tokens import (
    AdminTokenObtainPairSerializer,
    CollegeTokenObtainPairSerializer,
    ITTokenObtainPairSerializer,
    ProfessorTokenObtainPairSerializer,
)
from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.services.token_rotation_service import TokenRotationService
from apps.core.services.base import BaseService

WEB_JWT_DOMAINS = frozenset({"it", "professor", "college", "admin"})
TOKEN_SERIALIZER_BY_DOMAIN = {
    "it": ITTokenObtainPairSerializer,
    "professor": ProfessorTokenObtainPairSerializer,
    "college": CollegeTokenObtainPairSerializer,
    "admin": AdminTokenObtainPairSerializer,
}
USER_MODEL_BY_DOMAIN = {
    "it": ITUser,
    "professor": ProfessorUser,
    "college": CollegeUser,
    "admin": AdminUser,
}


class WebJWTService(BaseService):
    """Issue, refresh, and revoke JWT tokens via secure HttpOnly cookies."""

    @property
    def access_cookie(self) -> str:
        return getattr(settings, "JWT_ACCESS_COOKIE_NAME", "edunaukri_access")

    @property
    def refresh_cookie(self) -> str:
        return getattr(settings, "JWT_REFRESH_COOKIE_NAME", "edunaukri_refresh")

    @property
    def refresh_cookie_path(self) -> str:
        return getattr(settings, "JWT_REFRESH_COOKIE_PATH", "/")

    @property
    def legacy_refresh_cookie_paths(self) -> tuple[str, ...]:
        """Older deployments scoped refresh tokens to /auth/ only."""
        current = self.refresh_cookie_path.rstrip("/") or "/"
        paths = {current, "/auth/", "/auth"}
        if current != "/":
            paths.add("/")
        return tuple(paths)

    def issue_tokens(self, *, user, domain: str) -> tuple[str, str, uuid.UUID]:
        if domain not in WEB_JWT_DOMAINS:
            raise ValueError(
                f"Web JWT cookies are not supported for domain '{domain}'."
            )
        serializer_cls = TOKEN_SERIALIZER_BY_DOMAIN.get(domain)
        if serializer_cls is None:
            raise ValueError(f"No token serializer configured for domain '{domain}'.")
        session_uuid = uuid.uuid4()
        refresh = serializer_cls.get_token(user)
        refresh["session_uuid"] = str(session_uuid)
        return str(refresh.access_token), str(refresh), session_uuid

    def attach_tokens(
        self,
        response: HttpResponseBase,
        *,
        user,
        domain: str,
        request_meta: dict | None = None,
        auth_method: str = "password",
    ) -> HttpResponseBase:
        access, refresh, session_uuid = self.issue_tokens(user=user, domain=domain)
        secure = getattr(settings, "JWT_COOKIE_SECURE", not settings.DEBUG)
        samesite = getattr(settings, "JWT_COOKIE_SAMESITE", "Lax")

        access_max_age = int(
            settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
        )
        refresh_max_age = int(
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
        )

        response.set_cookie(
            self.access_cookie,
            access,
            max_age=access_max_age,
            httponly=True,
            secure=secure,
            samesite=samesite,
            path="/",
        )
        response.set_cookie(
            self.refresh_cookie,
            refresh,
            max_age=refresh_max_age,
            httponly=True,
            secure=secure,
            samesite=samesite,
            path=self.refresh_cookie_path,
        )
        for legacy_path in self.legacy_refresh_cookie_paths:
            if legacy_path.rstrip("/") != self.refresh_cookie_path.rstrip("/"):
                response.delete_cookie(self.refresh_cookie, path=legacy_path)
        meta = request_meta or getattr(response, "_request_meta", None) or {}
        self._register_login_session(
            user=user,
            domain=domain,
            refresh_token=refresh,
            session_uuid=session_uuid,
            request_meta=meta,
            auth_method=auth_method,
        )
        return response

    def attach_tokens_with_request(
        self,
        response: HttpResponseBase,
        *,
        user,
        domain: str,
        request=None,
        auth_method: str = "password",
    ) -> HttpResponseBase:
        meta = {}
        if request is not None:
            meta = {
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
            }
        return self.attach_tokens(
            response,
            user=user,
            domain=domain,
            request_meta=meta,
            auth_method=auth_method,
        )

    def _register_login_session(
        self,
        *,
        user,
        domain: str,
        refresh_token: str,
        session_uuid: uuid.UUID,
        request_meta: dict,
        auth_method: str = "password",
    ) -> None:
        try:
            SessionManagementService().register_session(
                domain=domain,
                user_id=user.pk,
                refresh_token=refresh_token,
                request_meta=request_meta,
                session_uuid=session_uuid,
                auth_method=auth_method,
            )
        except Exception:
            pass

    def clear_tokens(self, response: HttpResponseBase) -> HttpResponseBase:
        response.delete_cookie(self.access_cookie, path="/")
        for path in self.legacy_refresh_cookie_paths:
            response.delete_cookie(self.refresh_cookie, path=path)
        return response

    def refresh_access_token(
        self,
        *,
        refresh_token: str,
        request_meta: dict | None = None,
    ) -> tuple[str, str | None]:
        """Rotate refresh token and return new access (+ optional new refresh)."""
        return TokenRotationService().refresh_tokens(
            refresh_token=refresh_token,
            request_meta=request_meta,
        )

    def logout(
        self, *, refresh_token: str | None, request_meta: dict | None = None
    ) -> None:
        if not refresh_token:
            return
        try:
            token = RefreshToken(refresh_token)
            domain = token.get("domain")
            user_id = token.get("user_id")
            session_uuid = token.get("session_uuid")
            try:
                token.blacklist()
            except Exception:
                pass
            SessionManagementService().revoke_by_refresh_token(
                refresh_token, request_meta=request_meta
            )
            if domain and user_id:
                AuthAuditService().record_logout(
                    domain=domain,
                    user_id=user_id,
                    session_uuid=str(session_uuid) if session_uuid else None,
                    request_meta=request_meta,
                )
        except Exception:
            pass

    @staticmethod
    def resolve_it_user(request) -> ITUser | None:
        """Resolve the authenticated IT user from session or HttpOnly JWT cookies."""
        user = WebJWTService.resolve_web_user(request)
        if user is not None and isinstance(user, ITUser):
            return user
        return None

    @staticmethod
    def resolve_college_user(request) -> CollegeUser | None:
        """Resolve the authenticated College user from session or HttpOnly JWT cookies."""
        user = WebJWTService.resolve_web_user(request)
        if user is not None and isinstance(user, CollegeUser):
            return user
        return None

    @staticmethod
    def resolve_web_user(request):
        """Resolve authenticated IT, professor, college, or admin user from session or JWT cookies."""
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and isinstance(user, (ITUser, ProfessorUser, CollegeUser, AdminUser))
        ):
            loaded = WebJWTService._load_active_user(user)
            if loaded is not None:
                return loaded

        service = WebJWTService()
        access = request.COOKIES.get(service.access_cookie)
        if access:
            resolved = WebJWTService._user_from_access_token(access)
            if resolved is not None:
                return resolved

        refresh = request.COOKIES.get(service.refresh_cookie)
        if not refresh or not WebJWTService._refresh_token_is_usable(refresh):
            return None

        try:
            token = RefreshToken(refresh)
            domain = token.get("domain")
            user_id = token.get("user_id")
            if domain not in WEB_JWT_DOMAINS or not user_id:
                return None
            return WebJWTService._load_active_user_by_domain(domain, user_id)
        except Exception:
            return None

    @staticmethod
    def get_valid_it_user(request) -> ITUser | None:
        """Return an IT user only when session/JWT auth is present and the account may access the app."""
        user = WebJWTService.resolve_it_user(request)
        if user is None:
            return None
        if WebJWTService._account_block_reason(user) is not None:
            return None
        return user

    @staticmethod
    def get_valid_college_user(request) -> CollegeUser | None:
        """Return a College user only when session/JWT auth is present and the account may access the app."""
        user = WebJWTService.resolve_college_user(request)
        if user is None:
            return None
        if WebJWTService._account_block_reason(user) is not None:
            return None
        return user

    @staticmethod
    def get_valid_web_user(request):
        """Return any supported web-domain user when auth is valid."""
        user = WebJWTService.resolve_web_user(request)
        if user is None:
            return None
        if WebJWTService._account_block_reason(user) is not None:
            return None
        return user

    @staticmethod
    def _account_block_reason(user) -> str | None:
        from apps.authentication.validators.account_validator import (
            get_account_access_block_reason,
        )

        return get_account_access_block_reason(user)

    @staticmethod
    def _load_active_user(
        user,
    ) -> ITUser | ProfessorUser | CollegeUser | AdminUser | None:
        return WebJWTService._load_active_user_by_domain(
            WebJWTService._domain_for_user(user),
            user.pk,
        )

    @staticmethod
    def _domain_for_user(user) -> str | None:
        if isinstance(user, ITUser):
            return "it"
        if isinstance(user, ProfessorUser):
            return "professor"
        if isinstance(user, CollegeUser):
            return "college"
        if isinstance(user, AdminUser):
            return "admin"
        return None

    @staticmethod
    def _load_active_it_user(user_id) -> ITUser | None:
        user = WebJWTService._load_active_user_by_domain("it", user_id)
        return user if isinstance(user, ITUser) else None

    @staticmethod
    def _load_active_user_by_domain(domain: str, user_id):
        model = USER_MODEL_BY_DOMAIN.get(domain)
        if model is None:
            return None
        return model.objects.filter(
            pk=user_id, is_deleted=False, is_active=True
        ).first()

    @staticmethod
    def _refresh_token_is_usable(refresh: str) -> bool:
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )

            token = RefreshToken(refresh)
            jti = token.get("jti")
            if not jti:
                return True
            outstanding = OutstandingToken.objects.filter(jti=jti).first()
            if (
                outstanding
                and BlacklistedToken.objects.filter(token=outstanding).exists()
            ):
                return False
            return True
        except Exception:
            return True

    @staticmethod
    def _user_from_access_token(access: str):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import AccessToken

        try:
            token = AccessToken(access)
            domain = token.get("domain")
            user_id = token.get("user_id")
            if domain not in WEB_JWT_DOMAINS or not user_id:
                return None
            return WebJWTService._load_active_user_by_domain(domain, user_id)
        except TokenError:
            return None

    @staticmethod
    def resolve_it_dashboard_url(user) -> str:
        from apps.authentication.services.portal_url_service import PortalURLService

        return PortalURLService.dashboard_for_user(user)

    @staticmethod
    def resolve_dashboard_url(user) -> str:
        return WebJWTService.resolve_it_dashboard_url(user)
