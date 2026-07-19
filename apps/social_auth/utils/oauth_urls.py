"""Social Auth — OAuth redirect URI helpers.

Centralises the construction of OAuth callback redirect URIs.
Both LoginView and CallbackView must use these helpers — never
build redirect URIs inline or accept them from the frontend.
"""

from __future__ import annotations

from django.conf import settings


def google_redirect_uri() -> str:
    """Build the Google OAuth callback redirect URI from backend settings.

    The redirect URI is constructed by combining:
    1. ``OAUTH_REDIRECT_BASE`` — the backend's base URL (e.g. ``https://example.com``)
    2. The fixed Google callback path ``/api/social-auth/google/callback/``

    Returns:
        Full redirect URI string (e.g. ``https://example.com/api/social-auth/google/callback/``).

    Raises:
        ImproperlyConfigured: If ``OAUTH_REDIRECT_BASE`` is not set in Django settings.
    """
    base = getattr(settings, "OAUTH_REDIRECT_BASE", None)
    if not base:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            "OAUTH_REDIRECT_BASE must be set in Django settings. "
            "Example: OAUTH_REDIRECT_BASE=https://example.com"
        )
    return f"{base.rstrip('/')}/api/social-auth/google/callback/"


def linkedin_redirect_uri() -> str:
    """Build the LinkedIn OAuth callback redirect URI from backend settings.

    Returns:
        Full redirect URI string.

    Raises:
        ImproperlyConfigured: If ``OAUTH_REDIRECT_BASE`` is not set in Django settings.
    """
    base = getattr(settings, "OAUTH_REDIRECT_BASE", None)
    if not base:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            "OAUTH_REDIRECT_BASE must be set in Django settings. "
            "Example: OAUTH_REDIRECT_BASE=https://example.com"
        )
    return f"{base.rstrip('/')}/api/social-auth/linkedin/callback/"
