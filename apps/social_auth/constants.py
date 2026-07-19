"""Constants and configuration values for social authentication providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProviderName = Literal["google", "linkedin", "microsoft", "github"]


@dataclass(frozen=True)
class ProviderConfig:
    """Static configuration for a single OAuth provider."""

    name: ProviderName
    display_name: str
    scopes: tuple[str, ...]
    authorize_url: str
    token_url: str
    userinfo_url: str


# ---------------------------------------------------------------------------
# Provider base URLs — override via Django settings when needed.
# ---------------------------------------------------------------------------
GOOGLE_CONFIG = ProviderConfig(
    name="google",
    display_name="Google",
    scopes=(
        "openid",
        "email",
        "profile",
    ),
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
)

LINKEDIN_CONFIG = ProviderConfig(
    name="linkedin",
    display_name="LinkedIn",
    scopes=(
        "openid",
        "email",
        "profile",
    ),
    authorize_url="https://www.linkedin.com/oauth/v2/authorization",
    token_url="https://www.linkedin.com/oauth/v2/accessToken",
    userinfo_url="https://api.linkedin.com/v2/userinfo",
)

MICROSOFT_CONFIG = ProviderConfig(
    name="microsoft",
    display_name="Microsoft",
    scopes=(
        "openid",
        "email",
        "profile",
        "User.Read",
    ),
    authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
    userinfo_url="https://graph.microsoft.com/v1.0/me",
)

GITHUB_CONFIG = ProviderConfig(
    name="github",
    display_name="GitHub",
    scopes=(
        "read:user",
        "user:email",
    ),
    authorize_url="https://github.com/login/oauth/authorize",
    token_url="https://github.com/login/oauth/access_token",
    userinfo_url="https://api.github.com/user",
)

# Map provider name → config for programmatic look-up.
PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "google": GOOGLE_CONFIG,
    "linkedin": LINKEDIN_CONFIG,
    "microsoft": MICROSOFT_CONFIG,
    "github": GITHUB_CONFIG,
}
