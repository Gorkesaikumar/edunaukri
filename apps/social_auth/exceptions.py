"""Domain-specific exceptions for social authentication."""

from __future__ import annotations


class SocialAuthError(Exception):
    """Base exception for all social auth errors."""


class ProviderNotSupportedError(SocialAuthError):
    """Raised when an unknown/unconfigured provider is requested."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Social provider '{provider}' is not supported.")


class TokenExchangeError(SocialAuthError):
    """Raised when the OAuth token exchange with the provider fails."""

    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"Token exchange failed for '{provider}': {detail}")


class UserInfoFetchError(SocialAuthError):
    """Raised when fetching user profile info from the provider fails."""

    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"Failed to fetch user info from '{provider}': {detail}")


class AccountAlreadyLinkedError(SocialAuthError):
    """Raised when the social account is already linked to another local user."""

    def __init__(self, provider: str, provider_user_id: str) -> None:
        self.provider = provider
        self.provider_user_id = provider_user_id
        super().__init__(
            f"'{provider}' account {provider_user_id} is already linked to another user."
        )


class EmailNotVerifiedError(SocialAuthError):
    """Raised when the provider has not verified the user's email."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"'{provider}' did not provide a verified email.")


class InvalidTokenError(SocialAuthError):
    """Raised when an identity token is invalid, malformed, or fails signature verification."""

    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"Invalid token from '{provider}': {detail}")


class TokenExpiredError(InvalidTokenError):
    """Raised when the identity token has expired."""

    def __init__(self, provider: str) -> None:
        super().__init__(provider, detail="Token has expired.")


class InvalidAudienceError(InvalidTokenError):
    """Raised when the token's audience does not match the expected client ID."""

    def __init__(self, provider: str, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            provider,
            detail=f"Token audience '{actual}' does not match expected '{expected}'.",
        )


class TokenVerificationError(SocialAuthError):
    """Raised when the Google token verification library encounters an unexpected error."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Token verification failed: {detail}")


class CrossDomainLinkedError(SocialAuthError):
    """Raised when a Google account is already linked to a user in a different domain/role.

    The user attempted to sign in with Google from one portal (e.g. Faculty Professor)
    but their Google account is already linked to a user in a different portal
    (e.g. IT Job Seeker).  The error carries structured information so the frontend
    can display a clear "account already linked elsewhere" dialog.

    Attributes:
        email: The Google account email address.
        linked_domain: The domain of the existing linked user ("it", "professor", "college").
        linked_role: The role of the existing linked user ("seeker", "recruiter", "institution").
        linked_portal_display: Human-readable portal name (e.g. "IT Recruitment").
        linked_role_display: Human-readable role name (e.g. "Job Seeker").
        suggested_login_url: The correct login page URL for the existing account.
        linked_account_display: Combined human-readable account name (e.g. "IT Job Seeker").
    """

    def __init__(
        self,
        *,
        email: str,
        linked_domain: str,
        linked_role: str,
        linked_portal_display: str,
        linked_role_display: str,
        suggested_login_url: str,
        linked_account_display: str = "",
    ) -> None:
        self.email = email
        self.linked_domain = linked_domain
        self.linked_role = linked_role
        self.linked_portal_display = linked_portal_display
        self.linked_role_display = linked_role_display
        self.suggested_login_url = suggested_login_url
        self.linked_account_display = linked_account_display
        super().__init__(
            f"Google account {email} is already linked to a "
            f"{linked_portal_display} {linked_role_display} account. "
            f"Please use the {linked_portal_display} login page."
        )
