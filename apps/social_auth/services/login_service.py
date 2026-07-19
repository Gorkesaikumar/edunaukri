"""Google login service — authenticates a verified Google profile into the system.

Orchestrates the post-verification login flow:

1. **Resolve / create** the local user via ``GoogleAccountLinkingService``.
2. **Authenticate** the user by creating a Django session.
3. **Issue JWT tokens** (optional — attached to the HTTP response as HttpOnly cookies
   via ``WebJWTService``).
4. **Log** the authentication event via the audit service.
5. **Dispatch** the ``social_login_completed`` signal (lightweight handlers run
   inline; heavy work delegates to Celery).
6. **Return** the user, dashboard URL, and creation flag.

Does **not** verify tokens or query Google APIs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.services.base import BaseService
from apps.social_auth.exceptions import SocialAuthError
from apps.social_auth.services.account_linking_service import (
    GoogleAccountLinkingService,
)
from apps.social_auth.services.social_account_service import SocialAccountService
from apps.social_auth.signals import social_login_completed

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strongly-typed result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoogleLoginResult:
    """Result of the complete Google login flow.

    Designed to be serialised directly by the view into a JSON response.
    """

    user_id: str
    """UUID of the authenticated ``ITUser``."""

    email: str
    """Email address of the authenticated user."""

    was_created: bool
    """``True`` when a brand-new user account was registered in this flow."""

    dashboard_url: str
    """Role-aware dashboard URL to redirect the client to.

    Resolved via ``PortalURLService.dashboard_for_user()``.
    """

    user: object = field(repr=False)
    """The ``ITUser`` model instance — available so the view can pass it
    to ``attach_jwt()`` without an extra database query."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GoogleLoginService(BaseService):
    """Complete Google login orchestration — session, JWT, audit, and redirect.

    **Typical usage inside a DRF view**::

        service = GoogleLoginService()

        # 1. Log the user in (session + account linking + audit)
        result = service.login(request, profile=token_data)

        # 2. Attach JWT HttpOnly cookies to the response
        response = Response({"user_id": result.user_id, ...})
        if attach_jwt:
            service.attach_jwt(response, user=result.user, request=request)

        return response
    """

    def login(
        self,
        request,
        *,
        profile,
        domain: str = "it",
        role: str = "seeker",
    ) -> GoogleLoginResult:
        """Execute the core Google login flow.

        Steps performed:
        1. Resolve or create the local user (+ profile + roles)
           via ``GoogleAccountLinkingService``.
        2. Create a Django session (``SessionService.login_user``).
        3. Log the authentication event via ``AuthAuditService``.
        4. Dispatch the ``social_login_completed`` signal.
        5. Resolve the role-aware dashboard URL.

        Args:
            request: The Django / DRF ``HttpRequest`` — used for session
                creation and IP / user-agent metadata.
            profile: A verified ``GoogleTokenData`` instance.
            domain: User domain ("it", "professor", "college").
            role: User role within the domain ("seeker", "recruiter",
                "institution").

        Returns:
            ``GoogleLoginResult`` with identity, creation flag, dashboard
            URL, and the ``user`` instance for downstream use.

        **Does not verify tokens or query Google APIs.**
        """
        # ---- 1. Resolve or create the local user ----
        logger.info(
            "GoogleLoginService.login: domain=%s, role=%s, email=%s",
            domain, role, profile.email,
        )
        linking_result = GoogleAccountLinkingService().resolve_or_create(
            profile, domain=domain, role=role,
        )
        user = linking_result.user

        if user is None:
            raise SocialAuthError(
                f"Account linking failed for {profile.email}: "
                "GoogleAccountLinkingService returned a result with user=None. "
                "Check logs for orphaned SocialAccount or user creation failure."
            )

        logger.info(
            "GoogleLoginService.login: resolved user pk=%s, email=%s, was_created=%s",
            user.pk, getattr(user, 'email', '?'), linking_result.was_created,
        )

        # ---- 2. Create Django session (authenticates the user) ----
        SessionService().login_user(request, domain=domain, user=user)

        # ---- 3. Log the authentication event ----
        self._log_auth_event(request, user, domain=domain)

        # ---- 4. Dispatch the ``social_login_completed`` signal ----
        # Lightweight handlers (last_login, profile sync) run inline.
        # Heavy work (notification) runs via Celery.
        self._dispatch_signal(
            user=user,
            social_account_id=linking_result.social_account_id,
            provider="google",
            profile=profile,
        )

        # ---- 5. Build the dashboard URL ----
        dashboard_url = PortalURLService.dashboard_for_user(user)

        return GoogleLoginResult(
            user_id=str(user.pk),
            email=user.email,
            was_created=linking_result.was_created,
            dashboard_url=dashboard_url,
            user=user,
        )

    # ------------------------------------------------------------------
    # JWT attachment (optional — delegates to WebJWTService)
    # ------------------------------------------------------------------

    @staticmethod
    def attach_jwt(
        response,
        *,
        user,
        request=None,
        domain: str = "it",
    ):
        """Attach HttpOnly JWT cookies to an HTTP response.

        Thin wrapper around ``WebJWTService.attach_tokens_with_request``
        that sets the domain and auth method appropriately for the Google
        login flow.

        Args:
            response: The ``HttpResponseBase`` (or DRF ``Response``) to
                attach JWT cookies to.
            user: The user model instance (obtained from
                ``GoogleLoginResult.user``).
            request: Optional — provides IP / user-agent metadata for the
                session registration.
            domain: The user domain ("it", "professor", etc.). Defaults to
                ``"it"`` for backward compatibility.

        Returns:
            The same *response* with JWT cookies attached (for chaining).
        """
        return WebJWTService().attach_tokens_with_request(
            response,
            user=user,
            domain=domain,
            request=request,
            auth_method="google",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dispatch_signal(
        *,
        user,
        social_account_id: str,
        provider: str,
        profile=None,
    ) -> None:
        """Send the ``social_login_completed`` signal to all registered receivers.

        Keeps the ``send()`` call in one place so that provider-specific
        login services (Google, LinkedIn, etc.) all fire the same signal
        with a consistent signature.
        """
        social_login_completed.send(
            sender=GoogleLoginService,
            user=user,
            social_account_id=social_account_id,
            provider=provider,
            profile=profile,
        )

    @staticmethod
    def _log_auth_event(request, user, *, domain: str = "it") -> None:
        """Record a successful login event in the audit log."""
        AuthAuditService().record_login_success(
            domain=domain,
            user_id=user.pk,
            request_meta=_extract_meta(request),
            method="google",
        )


def _extract_meta(request):
    """Extract IP and user-agent from the request for audit logging."""
    if not request:
        return {}
    return {
        "ip_address": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
    }
