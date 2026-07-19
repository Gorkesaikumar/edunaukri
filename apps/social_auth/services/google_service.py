"""Google OAuth 2.0 ID token verification — verify and decode Google ID tokens.

Requires ``google-auth`` and ``requests``:

    pip install google-auth requests

Uses Google's official ``google.oauth2.id_token.verify_oauth2_token`` to
validate the token signature, expiry, issuer, and audience.  No database or
ORM access — pure token verification only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from django.conf import settings

import requests

from apps.social_auth.exceptions import (
    InvalidAudienceError,
    InvalidTokenError,
    TokenExchangeError,
    TokenExpiredError,
    TokenVerificationError,
)


@dataclass(frozen=True)
class GoogleAuthUrlResult:
    """Result returned when constructing the Google OAuth authorization URL."""

    authorize_url: str
    """Full URL to redirect the user to for Google sign-in."""

    state: str = field(default="")
    """CSRF state value that must be preserved and validated on callback."""


@dataclass(frozen=True)
class GoogleTokenData:
    """Verified and decoded payload extracted from a Google ID token."""

    google_user_id: str
    """Unique Google account identifier (the ``sub`` claim)."""

    email: str
    """Email address from the token (already normalized to lowercase)."""

    name: str
    """Display name returned by Google."""

    picture: str
    """URL of the Google profile picture (empty string if not provided)."""

    verified_email: bool
    """Whether Google has verified the email address (``email_verified`` claim)."""


class GoogleOAuthService:
    """Verifies Google ID tokens using Google's official ``google-auth`` library.

    This service performs **no database or ORM operations**.  It only
    validates the cryptographic integrity of an ID token and returns the
    decoded profile data.  Callers are responsible for persisting any
    account linking via ``SocialAccountService``.

    Usage::

        service = GoogleOAuthService()
        token_data = service.verify_id_token(id_token_str)
        # => GoogleTokenData(google_user_id="…", email="…", …)
    """

    def __init__(self) -> None:
        self._provider = "google"
        self._authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self._token_url = "https://oauth2.googleapis.com/token"
        self._scopes = "openid email profile"

    # ------------------------------------------------------------------
    # Public API — Step 1: Generate authorization URL
    # ------------------------------------------------------------------

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str = "",
        *,
        prompt: str = "select_account",
        access_type: str = "online",
    ) -> GoogleAuthUrlResult:
        """Build the Google OAuth 2.0 authorization URL.

        The user's browser should be redirected to this URL so they can
        authenticate with Google and grant consent.  After consent Google
        redirects back to *redirect_uri* with an authorization ``code``
        query parameter.

        Args:
            redirect_uri: Where Google redirects after consent. Must match
                exactly the URI registered in the Google Cloud Console.
            state: An opaque CSRF token that will be round-tripped by
                Google and must be validated on callback.
            prompt: ``"select_account"`` (default) always shows the
                account picker; ``"consent"`` forces the consent screen;
                ``"none"`` silently tries to authenticate.
            access_type: ``"online"`` (default) or ``"offline"`` for a
                refresh token.

        Returns:
            ``GoogleAuthUrlResult`` with the full ``authorize_url`` to
            redirect the user to.

        Raises:
            TokenVerificationError: If ``GOOGLE_OAUTH_CLIENT_ID`` is not
                configured in Django settings.
        """
        client_id = self._get_client_id()

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self._scopes,
            "access_type": access_type,
            "prompt": prompt,
        }
        if state:
            params["state"] = state

        url = f"{self._authorize_url}?{urlencode(params)}"
        return GoogleAuthUrlResult(authorize_url=url, state=state)

    # ------------------------------------------------------------------
    # Public API — Step 2: Exchange code → verify ID token → return profile
    # ------------------------------------------------------------------

    def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> GoogleTokenData:
        """Exchange an authorization code for a verified Google profile.

        Performs the full token-exchange handshake:

        1. POST the authorization *code* to Google's token endpoint.
        2. Extract the ``id_token`` from the JSON response.
        3. Verify the ID token's signature, expiry, audience, and issuer
           via ``google.oauth2.id_token.verify_oauth2_token``.
        4. Return the decoded profile as ``GoogleTokenData``.

        **No user login or database write occurs.**  The caller (typically
        a view or higher-level service) decides what to do with the
        verified profile (log in, register, link account, etc.).

        Args:
            code: The authorization code received from Google's redirect.
            redirect_uri: Must match the ``redirect_uri`` that was passed
                to ``get_authorization_url()``.

        Returns:
            ``GoogleTokenData`` with the verified Google profile.

        Raises:
            TokenExchangeError: If the HTTP request to the token endpoint
                fails, or the response does not contain an ``id_token``.
            InvalidTokenError: If the ID token fails signature, audience,
                or issuer validation.
            TokenExpiredError: If the ID token has expired.
            TokenVerificationError: If the ``google-auth`` library is
                missing or encounters an unexpected error.
        """
        token_data = self._fetch_tokens(code, redirect_uri)

        raw_id_token = token_data.get("id_token")
        if not raw_id_token:
            raise TokenExchangeError(
                self._provider,
                detail="Token response did not contain an ``id_token``.  "
                'Ensure the "openid" scope is included.',
            )

        return self.verify_id_token(raw_id_token)

    # ------------------------------------------------------------------
    # Public API — Step 3: Verify an existing ID token
    # ------------------------------------------------------------------

    def verify_id_token(
        self,
        id_token: str,
        client_id: str | None = None,
    ) -> GoogleTokenData:
        """Verify a Google ID token and extract profile information.

        Steps performed by the underlying ``google-auth`` library:

        1. **Signature verification** — validates the JWT signature using
           Google's public keys (fetched and cached automatically).
        2. **Expiry check** — rejects tokens whose ``exp`` claim is in the
           past.
        3. **Audience validation** — checks that the ``aud`` claim matches
           the provided *client_id*.
        4. **Issuer validation** — checks that the ``iss`` claim is
           ``https://accounts.google.com`` or ``accounts.google.com``.

        Args:
            id_token: The JWT string received from the Google sign-in
                client library.
            client_id: The OAuth 2.0 client ID that the token is intended
                for.  Defaults to ``settings.GOOGLE_OAUTH_CLIENT_ID``.

        Returns:
            A ``GoogleTokenData`` dataclass with the verified profile data.

        Raises:
            InvalidTokenError: If the token is malformed, has an invalid
                signature, or belongs to an unknown key.
            TokenExpiredError: If the token's expiration time has passed.
            InvalidAudienceError: If the token's audience does not match
                the expected client ID.
            TokenVerificationError: If the underlying library fails for
                an unexpected reason (network issue, etc.).
        """
        payload = self._verify(id_token, client_id or self._get_client_id())
        return self._extract(payload)

    # ------------------------------------------------------------------
    # Internal — token exchange
    # ------------------------------------------------------------------

    def _fetch_tokens(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange the authorization code for tokens at Google's token endpoint.

        POSTs to ``https://oauth2.googleapis.com/token`` with the
        authorization code, client credentials, and redirect URI.  The
        response includes ``access_token``, ``id_token`` (if the ``openid``
        scope was requested), ``expires_in``, and optionally
        ``refresh_token``.

        Args:
            code: The authorization code from Google's redirect.
            redirect_uri: The same redirect URI used in the authorization
                request (must match exactly).

        Returns:
            The parsed JSON response body as a dictionary.

        Raises:
            TokenExchangeError: If the HTTP request fails or the provider
                returns an error payload.
        """
        payload = {
            "code": code,
            "client_id": self._get_client_id(),
            "client_secret": self._get_client_secret(),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = requests.post(
                self._token_url,
                data=payload,
                timeout=20,
                headers={"Accept": "application/json"},
            )
        except requests.RequestException as exc:
            raise TokenExchangeError(
                self._provider,
                detail=f"HTTP request to token endpoint failed: {exc}",
            ) from exc

        if not response.ok:
            try:
                error_body = response.json()
            except json.JSONDecodeError:
                error_body = response.text[:500]

            error_description = ""
            if isinstance(error_body, dict):
                error_description = error_body.get(
                    "error_description",
                    error_body.get("error", ""),
                )
            else:
                error_description = str(error_body)

            raise TokenExchangeError(
                self._provider,
                detail=(
                    f"Token endpoint returned HTTP {response.status_code}: "
                    f"{error_description}"
                ),
            )

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise TokenExchangeError(
                self._provider,
                detail="Token endpoint returned non-JSON response.",
            ) from exc

    # ------------------------------------------------------------------
    # Internal — verification
    # ------------------------------------------------------------------

    def _verify(self, token: str, client_id: str) -> dict[str, Any]:
        """Delegate to ``google.oauth2.id_token.verify_oauth2_token``.

        This is a separate method to make it easy to mock or stub in tests
        without needing the real ``google-auth`` library.

        Raises:
            TokenVerificationError: If ``google-auth`` is not installed.
        """
        try:
            from google.auth import exceptions as google_auth_exceptions
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token
        except ImportError as exc:
            raise TokenVerificationError(
                detail="Missing required dependency: pip install google-auth requests",
            ) from exc

        try:
            request = google_requests.Request()
            payload = google_id_token.verify_oauth2_token(token, request, client_id)
        except google_auth_exceptions.ExpiredTokenError as exc:
            raise TokenExpiredError(self._provider) from exc
        except ValueError as exc:
            error_message = str(exc)

            if "audience" in error_message.lower():
                raise InvalidAudienceError(
                    self._provider,
                    expected=client_id,
                    actual=error_message,
                ) from exc

            raise InvalidTokenError(
                self._provider,
                detail=error_message or "Token verification failed.",
            ) from exc
        except google_auth_exceptions.GoogleAuthError as exc:
            raise InvalidTokenError(
                self._provider,
                detail=str(exc) or "Token signature or format verification failed.",
            ) from exc
        except Exception as exc:
            raise TokenVerificationError(
                detail=str(exc) or "Unexpected error during token verification.",
            ) from exc

        return payload

    @staticmethod
    def _get_client_id() -> str:
        """Return the Google OAuth client ID from Django settings."""
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        if not client_id:
            raise TokenVerificationError(
                detail="GOOGLE_OAUTH_CLIENT_ID is not configured in settings.",
            )
        return client_id

    @staticmethod
    def _get_client_secret() -> str:
        """Return the Google OAuth client secret from Django settings."""
        client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        if not client_secret:
            raise TokenVerificationError(
                detail="GOOGLE_OAUTH_CLIENT_SECRET is not configured in settings.",
            )
        return client_secret

    # ------------------------------------------------------------------
    # Internal — extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract(payload: dict[str, Any]) -> GoogleTokenData:
        """Extract and normalize profile data from the verified token payload.

        The Google ID token payload contains (at minimum):

        * ``sub`` — unique Google user ID (string)
        * ``email`` — email address (string)
        * ``email_verified`` — whether Google has verified the email (bool)
        * ``name`` — display name (string, optional)
        * ``picture`` — profile picture URL (string, optional)
        """
        return GoogleTokenData(
            google_user_id=str(payload.get("sub", "")),
            email=(payload.get("email") or "").lower().strip(),
            name=(payload.get("name") or "").strip(),
            picture=(payload.get("picture") or "").strip(),
            verified_email=bool(payload.get("email_verified", False)),
        )
