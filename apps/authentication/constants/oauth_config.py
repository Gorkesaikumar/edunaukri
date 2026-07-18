"""OAuth provider configuration helpers."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse

from apps.authentication.models import OAuthProvider


def oauth_redirect_base() -> str:
    return getattr(settings, "OAUTH_REDIRECT_BASE", "http://127.0.0.1:8000").rstrip("/")


def google_oauth_configured() -> bool:
    return bool(
        getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        and getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    )


def linkedin_oauth_configured() -> bool:
    return bool(
        getattr(settings, "LINKEDIN_OAUTH_CLIENT_ID", "")
        and getattr(settings, "LINKEDIN_OAUTH_CLIENT_SECRET", "")
    )


def provider_configured(provider: str) -> bool:
    if provider == OAuthProvider.GOOGLE:
        return google_oauth_configured()
    if provider == OAuthProvider.LINKEDIN:
        return linkedin_oauth_configured()
    return False


def callback_url(provider: str) -> str:
    name = f"oauth_{provider}_callback"
    return f"{oauth_redirect_base()}{reverse(name)}"
