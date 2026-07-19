"""LinkedIn OAuth 2.0 service — token exchange and user-info retrieval."""

from __future__ import annotations


class LinkedInOAuthService:
    """Handles LinkedIn OAuth 2.0 token exchange and user profile retrieval."""

    def __init__(self) -> None:
        self._provider = "linkedin"

    # def exchange_code(self, code: str, redirect_uri: str) -> OAuthToken:
    #     """Exchange an authorization code for an access token."""
    #     ...

    # def get_user_info(self, access_token: str) -> dict:
    #     """Retrieve the authenticated user's profile from LinkedIn."""
    #     ...

    # def refresh_token(self, refresh_token: str) -> OAuthToken:
    #     """Refresh an expired access token."""
    #     ...
