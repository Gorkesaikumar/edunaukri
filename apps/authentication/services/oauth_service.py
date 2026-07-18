"""Google and LinkedIn OAuth 2.0 / OpenID Connect for IT web authentication."""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.core.exceptions import ValidationError

from apps.authentication.constants.oauth_config import callback_url, provider_configured
from apps.authentication.models import OAuthProvider
from apps.authentication.services.oauth_account_service import (
    OAuthAccountService,
    OAuthIdentity,
)
from apps.core.services.base import BaseService


@dataclass(frozen=True)
class OAuthStartResult:
    authorize_url: str
    state: str


class OAuthService(BaseService):
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

    LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

    SESSION_STATE_KEY = "oauth_state"
    SESSION_PROVIDER_KEY = "oauth_provider"
    SESSION_ROLE_KEY = "oauth_intended_role"
    SESSION_INTENT_KEY = "oauth_intent"
    SESSION_RETURN_KEY = "oauth_return_url"

    def start_authorization(
        self,
        *,
        provider: str,
        role: str,
        request,
        intent: str = "login",
        return_url: str = "",
    ) -> OAuthStartResult:
        if provider not in OAuthProvider.values:
            raise ValidationError("Unknown OAuth provider.")
        if not provider_configured(provider):
            raise ValidationError(f"{provider.title()} sign-in is not configured yet.")
        if role == "institution":
            role = "college"
        if intent == "connect":
            if role not in ("seeker", "recruiter", "professor", "college"):
                role = "seeker"
        elif role not in ("seeker", "recruiter", "professor", "college"):
            raise ValidationError("Invalid account type.")

        state = secrets.token_urlsafe(32)
        request.session[self.SESSION_STATE_KEY] = state
        request.session[self.SESSION_PROVIDER_KEY] = provider
        request.session[self.SESSION_ROLE_KEY] = role
        request.session[self.SESSION_INTENT_KEY] = intent
        request.session[self.SESSION_RETURN_KEY] = return_url or ""

        if provider == OAuthProvider.GOOGLE:
            url = self._google_authorize_url(state)
        else:
            url = self._linkedin_authorize_url(state)
        return OAuthStartResult(authorize_url=url, state=state)

    def complete_authorization(self, *, provider: str, request):
        expected_state = request.session.pop(self.SESSION_STATE_KEY, "")
        session_provider = request.session.pop(self.SESSION_PROVIDER_KEY, "")
        intended_role = request.session.pop(self.SESSION_ROLE_KEY, "seeker")
        intent = request.session.pop(self.SESSION_INTENT_KEY, "login")
        return_url = request.session.pop(self.SESSION_RETURN_KEY, "")

        state = request.GET.get("state", "")
        if not expected_state or state != expected_state:
            raise ValidationError("OAuth session expired. Please try again.")
        if session_provider != provider:
            raise ValidationError("OAuth provider mismatch.")

        error = request.GET.get("error")
        if error:
            description = request.GET.get("error_description", error)
            raise ValidationError(description)

        code = request.GET.get("code")
        if not code:
            raise ValidationError("Authorization code missing.")

        if provider == OAuthProvider.GOOGLE:
            identity = self._google_identity(code, redirect_uri=callback_url(provider))
        else:
            identity = self._linkedin_identity(
                code, redirect_uri=callback_url(provider)
            )

        if intent == "connect":
            from apps.accounts.models.college_user import CollegeUser
            from apps.accounts.models.professor_user import ProfessorUser
            from apps.authentication.services.college_oauth_account_service import (
                CollegeOAuthAccountService,
            )
            from apps.authentication.services.professor_oauth_account_service import (
                ProfessorOAuthAccountService,
            )
            from apps.authentication.services.web_jwt_service import WebJWTService

            if intended_role == "professor":
                user = WebJWTService.get_valid_web_user(request)
                if user is None or not isinstance(user, ProfessorUser):
                    raise ValidationError(
                        "Sign in required to connect social accounts."
                    )
                ProfessorOAuthAccountService().link_provider_to_user(user, identity)
                return user, intended_role, intent, return_url
            if intended_role == "college":
                user = WebJWTService.get_valid_web_user(request)
                if user is None or not isinstance(user, CollegeUser):
                    raise ValidationError(
                        "Sign in required to connect social accounts."
                    )
                CollegeOAuthAccountService().link_provider_to_user(user, identity)
                return user, intended_role, intent, return_url

            user = WebJWTService.get_valid_it_user(request)
            if user is None:
                raise ValidationError("Sign in required to connect social accounts.")
            OAuthAccountService().link_provider_to_user(user, identity)
            return user, intended_role, intent, return_url

        if intended_role == "professor":
            from apps.authentication.services.professor_oauth_account_service import (
                ProfessorOAuthAccountService,
            )

            user = ProfessorOAuthAccountService().resolve_or_create_professor_user(
                identity
            )
            return user, intended_role, intent, return_url
        if intended_role == "college":
            from apps.authentication.services.college_oauth_account_service import (
                CollegeOAuthAccountService,
            )

            user = CollegeOAuthAccountService().resolve_or_create_college_user(identity)
            return user, intended_role, intent, return_url

        user = OAuthAccountService().resolve_or_create_it_user(
            identity, intended_role=intended_role
        )
        return user, intended_role, intent, return_url

    def _google_authorize_url(self, state: str) -> str:
        from django.conf import settings

        params = {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": callback_url(OAuthProvider.GOOGLE),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{self.GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def _linkedin_authorize_url(self, state: str) -> str:
        from django.conf import settings

        params = {
            "response_type": "code",
            "client_id": settings.LINKEDIN_OAUTH_CLIENT_ID,
            "redirect_uri": callback_url(OAuthProvider.LINKEDIN),
            "state": state,
            "scope": "openid profile email",
        }
        return f"{self.LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def _google_identity(self, code: str, *, redirect_uri: str) -> OAuthIdentity:
        from django.conf import settings

        token_payload = self._post_form(
            self.GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        access_token = token_payload.get("access_token")
        if not access_token:
            raise ValidationError("Could not obtain Google access token.")
        profile = self._get_json(
            self.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        email = (profile.get("email") or "").lower().strip()
        if not email:
            raise ValidationError("Google did not provide an email address.")
        first, last = self._split_name(
            profile.get("name", ""),
            profile.get("given_name"),
            profile.get("family_name"),
        )
        return OAuthIdentity(
            provider=OAuthProvider.GOOGLE,
            provider_user_id=str(profile.get("sub") or ""),
            email=email,
            first_name=first,
            last_name=last,
            email_verified=bool(profile.get("email_verified", True)),
        )

    def _linkedin_identity(self, code: str, *, redirect_uri: str) -> OAuthIdentity:
        from django.conf import settings

        token_payload = self._post_form(
            self.LINKEDIN_TOKEN_URL,
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.LINKEDIN_OAUTH_CLIENT_ID,
                "client_secret": settings.LINKEDIN_OAUTH_CLIENT_SECRET,
            },
        )
        access_token = token_payload.get("access_token")
        if not access_token:
            raise ValidationError("Could not obtain LinkedIn access token.")
        profile = self._get_json(
            self.LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        email = (profile.get("email") or "").lower().strip()
        if not email:
            raise ValidationError("LinkedIn did not provide an email address.")
        first, last = self._split_name(
            profile.get("name", ""),
            profile.get("given_name"),
            profile.get("family_name"),
        )
        return OAuthIdentity(
            provider=OAuthProvider.LINKEDIN,
            provider_user_id=str(profile.get("sub") or ""),
            email=email,
            first_name=first,
            last_name=last,
            email_verified=bool(profile.get("email_verified", True)),
        )

    @staticmethod
    def _split_name(
        full_name: str, given: str | None, family: str | None
    ) -> tuple[str, str]:
        if given or family:
            return (given or "").strip(), (family or "").strip()
        parts = (full_name or "").strip().split(None, 1)
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], parts[0]
        return parts[0], parts[1]

    @staticmethod
    def _post_form(url: str, data: dict) -> dict:
        encoded = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise ValidationError(f"OAuth token exchange failed: {body[:200]}") from exc

    @staticmethod
    def _get_json(url: str, *, headers: dict | None = None) -> dict:
        req = urllib.request.Request(url, method="GET")
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise ValidationError(
                f"OAuth profile request failed: {body[:200]}"
            ) from exc

    @staticmethod
    def _meta(request) -> dict:
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
