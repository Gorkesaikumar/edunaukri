"""
Social Auth — views
Thin view layer delegating to services. No business logic here.

OAuth State Context Preservation
--------------------------------
The OAuth ``state`` parameter is a signed (HMAC) JSON object containing the
login context: domain, role, and the login_url (the page the user was on when
clicking "Continue with Google").  It is:

1. Created by ``GoogleLoginView`` when the frontend initiates OAuth.
2. Passed through to Google's authorization endpoint (unmodified).
3. Returned by Google in the callback query string (unmodified).
4. Verified and unsigned by ``GoogleCallbackView``.

On success: 302 redirect → dashboard URL (with JWT cookies).
On failure: 302 redirect → ORIGINAL login page (from state) with ``?oauth_error=...``.

This ensures users are never sent to a generic /login that doesn't exist
in the application's domain-scoped URL structure.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import HttpResponseRedirect

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions.domain_exceptions import DomainException
from apps.social_auth.exceptions import CrossDomainLinkedError, SocialAuthError
from apps.social_auth.serializers import (
    GoogleCallbackSerializer,
    GoogleLoginSerializer,
)
from apps.social_auth.services.google_service import GoogleOAuthService
from apps.social_auth.services.login_service import GoogleLoginService
from apps.social_auth.utils.oauth_urls import google_redirect_uri

logger = logging.getLogger(__name__)

# Maximum age (seconds) for a signed OAuth state token.
OAUTH_STATE_MAX_AGE = 10 * 60  # 10 minutes


# ---------------------------------------------------------------------------
# Login page URLs (domain + role → login page path)
# Used as fallback when state is invalid/expired and login_url
# cannot be extracted from it.
# ---------------------------------------------------------------------------

LOGIN_PAGE_MAP = {
    ("it", "seeker"): "/it/login/job-seeker/",
    ("it", "recruiter"): "/it/login/recruiter/",
    ("professor", "seeker"): "/faculty/login/professor/",
    ("college", "institution"): "/faculty/login/institution/",
}

DEFAULT_FALLBACK_LOGIN = "/it/login/job-seeker/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_login_url(*, domain: str | None = None, role: str | None = None) -> str:
    """Resolve the correct login page URL for a given domain+role combination.

    Falls back to ``DEFAULT_FALLBACK_LOGIN`` (IT job seeker) when the
    combination is unknown.
    """
    if domain and role:
        return LOGIN_PAGE_MAP.get((domain, role), DEFAULT_FALLBACK_LOGIN)
    return DEFAULT_FALLBACK_LOGIN


def _sign_oauth_state(*, domain: str, role: str, login_url: str = "") -> str:
    """Sign the OAuth context into a tamper-proof state token.

    ``login_url`` is the exact login page path the user was on when they
    clicked "Continue with Google".  On callback failure, this path is
    used for the error redirect so the user returns to the SAME login page.
    """
    signer = TimestampSigner()
    return signer.sign_object(
        {"domain": domain, "role": role, "login_url": login_url},
    )


def _unsign_oauth_state(state: str) -> dict:
    """Validate and unsign an OAuth state token.

    Returns:
        ``{"domain": ..., "role": ..., "login_url": ...}`` on success.

    Raises:
        ``BadSignature``: If the token has been tampered with.
        ``SignatureExpired``: If the token is older than
            ``OAUTH_STATE_MAX_AGE``.
    """
    signer = TimestampSigner()
    return signer.unsign_object(
        state,
        max_age=OAUTH_STATE_MAX_AGE,
    )


def _login_error_redirect(*, message: str, login_url: str | None = None) -> HttpResponseRedirect:
    """Redirect the browser to a login page with an OAuth error message.

    Args:
        message: The error message to display.
        login_url: The login page URL to redirect to.  If ``None``, falls
            back to ``DEFAULT_FALLBACK_LOGIN``.

    Returns:
        An ``HttpResponseRedirect`` to ``{login_url}?oauth_error={message}``.
    """
    target = login_url or DEFAULT_FALLBACK_LOGIN
    query = urlencode({"oauth_error": message})
    return HttpResponseRedirect(f"{target}?{query}")


def _cross_domain_redirect(*, error: CrossDomainLinkedError, login_url: str | None = None) -> HttpResponseRedirect:
    """Redirect the browser to the original login page with the linked account name.

    The frontend JS detects the ``oauth_linked_account`` param and displays
    a simplified modal dialog showing only the portal/role name.

    Query parameter:
        oauth_linked_account — Combined human-readable account name
            (e.g. "IT Job Seeker", "Faculty Professor")
    """
    target = login_url or DEFAULT_FALLBACK_LOGIN
    query = urlencode({
        "oauth_linked_account": error.linked_account_display
        or f"{error.linked_portal_display} {error.linked_role_display}".strip(),
    })
    return HttpResponseRedirect(f"{target}?{query}")


def _execute_callback(request, code: str, domain: str = "it", role: str = "seeker"):
    """Shared OAuth callback logic — exchange code, login, attach JWT cookies.

    Both ``domain`` and ``role`` come from the signed OAuth ``state``
    token and are passed through to the linking service so the correct
    user model and profile type are created.

    Returns:
        ``GoogleLoginResult`` on success.

    Raises:
        SocialAuthError: On OAuth-specific failures (bad code, etc.).
        Exception: On unexpected errors.
    """
    redirect_uri = google_redirect_uri()

    # 1. Exchange authorization code for a verified Google profile
    google_service = GoogleOAuthService()
    token_data = google_service.exchange_code(
        code=code,
        redirect_uri=redirect_uri,
    )

    # 2. Login / create account (domain+role-aware)
    login_service = GoogleLoginService()
    login_result = login_service.login(
        request=request,
        profile=token_data,
        domain=domain,
        role=role,
    )

    return login_result


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


class GoogleLoginView(APIView):
    """Step 1: Initiate a Google sign-in flow.

    **POST** ``/api/social-auth/google/login/``

    Request body::

        {
            "domain": "it",
            "role": "seeker",
            "login_url": "/it/login/job-seeker/"
        }

    The ``domain``, ``role``, and ``login_url`` are signed into the OAuth
    ``state`` parameter so the callback knows the login context and where
    to redirect on error.

    Response ``200``::

        {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
            "state": "signed_token..."
        }

    The client should redirect the user's browser to ``authorize_url``.
    The ``state`` value is automatically round-tripped by Google and
    will be present on the callback.

    The redirect URI is constructed server-side from
    ``settings.OAUTH_REDIRECT_BASE`` + the fixed callback path.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        domain = serializer.validated_data.get("domain", "it")
        role = serializer.validated_data.get("role", "seeker")
        login_url = serializer.validated_data.get("login_url", "")

        # Build the signed state token containing the login context
        state = _sign_oauth_state(domain=domain, role=role, login_url=login_url)

        # Build redirect URI server-side — never accept from frontend
        redirect_uri = google_redirect_uri()

        result = GoogleOAuthService().get_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
        )

        return Response(
            {
                "authorize_url": result.authorize_url,
                "state": state,
            },
        )


class GoogleCallbackView(APIView):
    """
    Step 2: Complete Google OAuth callback.

    Two modes:
    - **GET**  — Browser redirect from Google.  The signed ``state``
                 parameter (created by ``GoogleLoginView``) is extracted
                 to recover the login context (domain, role, login_url).
                 On failure, redirects to the ORIGINAL login page.
    - **POST** — API clients.  Same logic but returns JSON.
    """

    authentication_classes = []
    permission_classes = []

    # ------------------------------------------------------------------
    # Browser flow (Google redirects here from the OAuth dialog)
    # ------------------------------------------------------------------

    def get(self, request: Request, *args, **kwargs):
        """
        Google redirects the browser here with:

            GET /api/social-auth/google/callback/?code=...&state=...

        The ``state`` parameter is the signed token created by
        ``GoogleLoginView``.  It contains domain, role, and login_url.

        On success: 302 redirect → dashboard URL (with JWT cookies).
        On failure: 302 redirect → ORIGINAL login page ``?oauth_error=...``.
        """
        code = request.query_params.get("code")
        if not code:
            return _login_error_redirect(message="Missing authorization code.")

        state = request.query_params.get("state", "")

        # Recover login context from the signed state token.
        domain = "it"
        role = "seeker"
        login_url = None
        try:
            context = _unsign_oauth_state(state)
            domain = context.get("domain", "it")
            role = context.get("role", "seeker")
            login_url = context.get("login_url") or None
        except (BadSignature, SignatureExpired):
            logger.warning(
                "Invalid or expired OAuth state token: %s...",
                state[:40] if state else "(empty)",
            )
            # Use domain+role fallback since the state is invalid
            return _login_error_redirect(
                message="Your sign-in session expired. Please try again.",
                login_url=_resolve_login_url(domain=domain, role=role),
            )

        try:
            login_result = _execute_callback(request, code, domain=domain, role=role)
        except CrossDomainLinkedError as exc:
            logger.info(
                "GET OAuth cross-domain link: %s → %s/%s (linked to %s/%s)",
                exc.email, domain, role, exc.linked_domain, exc.linked_role,
            )
            return _cross_domain_redirect(
                error=exc,
                login_url=login_url or _resolve_login_url(domain=domain, role=role),
            )
        except SocialAuthError as exc:
            logger.warning("GET OAuth callback failed: %s", exc)
            return _login_error_redirect(
                message=str(exc),
                login_url=login_url or _resolve_login_url(domain=domain, role=role),
            )
        except DomainException as exc:
            # Domain-specific errors (ConflictException, ValidationException, etc.)
            # are not SocialAuthErrors but are expected domain-layer failures.
            logger.warning("GET OAuth callback domain error: %s", exc)
            error_msg = str(exc)
            if settings.DEBUG:
                error_msg = f"{exc.__class__.__name__}: {exc}"
            return _login_error_redirect(
                message=error_msg or "Account setup failed. Please try again.",
                login_url=login_url or _resolve_login_url(domain=domain, role=role),
            )
        except Exception as exc:
            logger.exception("GET OAuth callback failed unexpectedly")
            error_msg = "An unexpected error occurred during sign-in. Please try again."
            if settings.DEBUG:
                error_msg = f"{exc.__class__.__name__}: {exc}"
            return _login_error_redirect(
                message=error_msg,
                login_url=login_url or _resolve_login_url(domain=domain, role=role),
            )

        # Build a 302 redirect to the user's dashboard
        dashboard_url = login_result.dashboard_url
        response = HttpResponseRedirect(dashboard_url)

        # Attach JWT cookies to the redirect response
        GoogleLoginService.attach_jwt(
            response=response,
            user=login_result.user,
            request=request,
            domain=domain,
        )

        return response

    # ------------------------------------------------------------------
    # API flow (programmatic clients)
    # ------------------------------------------------------------------

    def post(self, request: Request, *args, **kwargs):
        """
        API clients POST to this endpoint after obtaining an authorization code.

        Body::

            {"code": "...", "state": "..."}

        The ``state`` was returned by ``GoogleLoginView``.  It is verified
        for authenticity and expiry here.

        Response ``200``::

            {
                "user_id": "...",
                "email": "...",
                "was_created": true,
                "dashboard_url": "/jobseeker/<uuid>/dashboard/"
            }
        """
        serializer = GoogleCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        state = serializer.validated_data.get("state", "")

        # Recover login context from the signed state token.
        domain = "it"
        role = "seeker"
        try:
            context = _unsign_oauth_state(state)
            domain = context.get("domain", "it")
            role = context.get("role", "seeker")
        except (BadSignature, SignatureExpired):
            return Response(
                {
                    "error": "Invalid or expired sign-in session. Please try again.",
                    "code": "InvalidOAuthState",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            login_result = _execute_callback(request, code, domain=domain, role=role)
        except CrossDomainLinkedError as exc:
            logger.info(
                "POST OAuth cross-domain link: %s → %s/%s (linked to %s/%s)",
                exc.email, domain, role, exc.linked_domain, exc.linked_role,
            )
            return Response(
                {
                    "error": "This Google account is already linked to another portal.",
                    "code": "CrossDomainLinked",
                    "linked_email": exc.email,
                    "linked_domain": exc.linked_domain,
                    "linked_role": exc.linked_role,
                    "linked_portal_display": exc.linked_portal_display,
                    "linked_role_display": exc.linked_role_display,
                    "suggested_login_url": exc.suggested_login_url,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except SocialAuthError as exc:
            return Response(
                {"error": str(exc), "code": exc.__class__.__name__},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DomainException as exc:
            logger.warning("POST OAuth callback domain error: %s", exc)
            return Response(
                {
                    "error": str(exc) or "Account setup failed.",
                    "code": exc.__class__.__name__,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Google callback failed unexpectedly")
            error_msg = str(exc) or "An unexpected error occurred."
            if settings.DEBUG:
                error_msg = f"{exc.__class__.__name__}: {exc}"
            return Response(
                {
                    "error": error_msg,
                    "type": exc.__class__.__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # JSON response for API clients
        response = Response(
            {
                "user_id": login_result.user_id,
                "email": login_result.email,
                "was_created": login_result.was_created,
                "dashboard_url": login_result.dashboard_url,
            },
            status=status.HTTP_200_OK,
        )

        # Attach JWT cookies to the JSON response
        GoogleLoginService.attach_jwt(
            response=response,
            user=login_result.user,
            request=request,
            domain=domain,
        )

        return response