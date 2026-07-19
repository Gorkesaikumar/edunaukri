"""Tests for social_auth exception classes."""

from __future__ import annotations

from apps.social_auth.exceptions import (
    AccountAlreadyLinkedError,
    EmailNotVerifiedError,
    InvalidAudienceError,
    InvalidTokenError,
    ProviderNotSupportedError,
    SocialAuthError,
    TokenExchangeError,
    TokenExpiredError,
    TokenVerificationError,
    UserInfoFetchError,
)


class TestSocialAuthExceptions:
    """Verify that each exception is a subclass of SocialAuthError and
    produces a sensible string."""

    def test_social_auth_error_is_base(self):
        """SocialAuthError should be the base exception."""
        exc = SocialAuthError("something went wrong")
        assert str(exc) == "something went wrong"

    def test_provider_not_supported(self):
        exc = ProviderNotSupportedError("fakeprovider")
        assert isinstance(exc, SocialAuthError)
        assert exc.provider == "fakeprovider"
        assert "fakeprovider" in str(exc)

    def test_token_exchange_error(self):
        exc = TokenExchangeError("google", "HTTP 400")
        assert isinstance(exc, SocialAuthError)
        assert exc.provider == "google"
        assert exc.detail == "HTTP 400"
        assert "google" in str(exc)
        assert "HTTP 400" in str(exc)

    def test_user_info_fetch_error(self):
        exc = UserInfoFetchError("linkedin", "network error")
        assert isinstance(exc, SocialAuthError)
        assert exc.provider == "linkedin"
        assert "linkedin" in str(exc)
        assert "network error" in str(exc)

    def test_account_already_linked_error(self):
        exc = AccountAlreadyLinkedError("google", "user_abc")
        assert isinstance(exc, SocialAuthError)
        assert exc.provider == "google"
        assert exc.provider_user_id == "user_abc"
        assert "google" in str(exc)
        assert "user_abc" in str(exc)

    def test_email_not_verified_error(self):
        exc = EmailNotVerifiedError("google")
        assert isinstance(exc, SocialAuthError)
        assert exc.provider == "google"
        assert "google" in str(exc)

    def test_invalid_token_error(self):
        exc = InvalidTokenError("google", "bad signature")
        assert isinstance(exc, SocialAuthError)
        assert exc.provider == "google"
        assert "bad signature" in str(exc)

    def test_token_expired_error(self):
        exc = TokenExpiredError("google")
        assert isinstance(exc, InvalidTokenError)  # subclass of InvalidTokenError
        assert exc.provider == "google"
        assert "expired" in str(exc)

    def test_invalid_audience_error(self):
        exc = InvalidAudienceError(
            "google",
            expected="my-client-id",
            actual="wrong-client-id",
        )
        assert isinstance(exc, InvalidTokenError)
        assert exc.provider == "google"
        assert exc.expected == "my-client-id"
        assert exc.actual == "wrong-client-id"
        assert "wrong-client-id" in str(exc)
        assert "my-client-id" in str(exc)

    def test_token_verification_error(self):
        exc = TokenVerificationError("library not found")
        assert isinstance(exc, SocialAuthError)
        assert "library not found" in str(exc)
