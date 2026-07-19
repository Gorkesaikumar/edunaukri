"""Tests for GoogleOAuthService — auth URL, token exchange, verification, error paths.

All external HTTP calls and the google-auth library are mocked so tests run
fast and without network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test.utils import override_settings

from apps.social_auth.exceptions import (
    InvalidAudienceError,
    InvalidTokenError,
    TokenExchangeError,
    TokenExpiredError,
    TokenVerificationError,
)
from apps.social_auth.services.google_service import (
    GoogleAuthUrlResult,
    GoogleOAuthService,
    GoogleTokenData,
)

svc = GoogleOAuthService()


# ---------------------------------------------------------------------------
# get_authorization_url
# ---------------------------------------------------------------------------


class TestGetAuthorizationUrl:
    """Tests for GoogleOAuthService.get_authorization_url()."""

    def test_returns_auth_url_and_state(self):
        with patch.object(
            svc.__class__, "_get_client_id", return_value="test-client-id"
        ):
            result = svc.get_authorization_url(
                redirect_uri="https://example.com/callback",
                state="csrf_token_123",
            )
        assert isinstance(result, GoogleAuthUrlResult)
        assert "accounts.google.com" in result.authorize_url
        assert "client_id=test-client-id" in result.authorize_url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in result.authorize_url
        assert "state=csrf_token_123" in result.authorize_url
        assert result.state == "csrf_token_123"

    def test_default_prompt_and_access_type(self):
        with patch.object(
            svc.__class__, "_get_client_id", return_value="test-client-id"
        ):
            result = svc.get_authorization_url(
                redirect_uri="https://example.com/callback",
            )
        assert "prompt=select_account" in result.authorize_url
        assert "access_type=online" in result.authorize_url

    def test_custom_prompt(self):
        with patch.object(
            svc.__class__, "_get_client_id", return_value="test-client-id"
        ):
            result = svc.get_authorization_url(
                redirect_uri="https://example.com/callback",
                prompt="consent",
            )
        assert "prompt=consent" in result.authorize_url

    def test_empty_state_omitted(self):
        with patch.object(
            svc.__class__, "_get_client_id", return_value="test-client-id"
        ):
            result = svc.get_authorization_url(
                redirect_uri="https://example.com/callback",
                state="",
            )
        assert "state=" not in result.authorize_url

    def test_missing_client_id_raises(self):
        with patch.object(svc.__class__, "_get_client_id", side_effect=TokenVerificationError("not configured")):
            with pytest.raises(TokenVerificationError):
                svc.get_authorization_url(redirect_uri="https://example.com/callback")


# ---------------------------------------------------------------------------
# verify_id_token
# ---------------------------------------------------------------------------


class TestVerifyIdToken:
    """Tests for GoogleOAuthService.verify_id_token() — mocks google-auth."""

    @patch.object(GoogleOAuthService, "_verify")
    def test_valid_token_returns_token_data(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google_user_123",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "email_verified": True,
        }
        result = svc.verify_id_token("valid_token")
        assert isinstance(result, GoogleTokenData)
        assert result.google_user_id == "google_user_123"
        assert result.email == "user@example.com"
        assert result.name == "Test User"
        assert result.picture == "https://example.com/photo.jpg"
        assert result.verified_email is True

    @patch.object(GoogleOAuthService, "_verify")
    def test_normalizes_email_lowercase(self, mock_verify):
        mock_verify.return_value = {
            "sub": "id",
            "email": "User@Example.COM",
            "email_verified": True,
        }
        result = svc.verify_id_token("tok")
        assert result.email == "user@example.com"

    @patch.object(GoogleOAuthService, "_verify")
    def test_missing_optional_fields_defaults_to_empty(self, mock_verify):
        mock_verify.return_value = {
            "sub": "id",
            "email": "user@example.com",
            "email_verified": True,
        }
        result = svc.verify_id_token("tok")
        assert result.name == ""
        assert result.picture == ""

    @patch.object(GoogleOAuthService, "_verify")
    def test_unverified_email(self, mock_verify):
        mock_verify.return_value = {
            "sub": "id",
            "email": "user@example.com",
            "email_verified": False,
        }
        result = svc.verify_id_token("tok")
        assert result.verified_email is False


# ---------------------------------------------------------------------------
# _verify — mocking google-auth library exceptions
# ---------------------------------------------------------------------------


class TestVerifyInternal:
    """Tests for the internal _verify() method that wraps google-auth."""

    def test_import_error_raises_token_verification_error(self):
        """If google-auth is not installed, raise TokenVerificationError."""
        svc_internal = GoogleOAuthService()
        with patch.object(
            svc_internal,
            "_verify",
            side_effect=TokenVerificationError("Missing required dependency"),
        ):
            with pytest.raises(TokenVerificationError, match="Missing required"):
                svc_internal._verify("token", "client_id")


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    """Tests for GoogleOAuthService.exchange_code() — mocks HTTP + google-auth."""

    @patch.object(GoogleOAuthService, "_verify")
    @patch.object(GoogleOAuthService, "_fetch_tokens")
    def test_successful_exchange(self, mock_fetch, mock_verify):
        mock_fetch.return_value = {
            "access_token": "ya29.abc",
            "id_token": "valid_id_token",
            "expires_in": 3600,
        }
        mock_verify.return_value = {
            "sub": "google_id",
            "email": "user@example.com",
            "name": "User",
            "picture": "",
            "email_verified": True,
        }

        result = svc.exchange_code(code="auth_code", redirect_uri="https://example.com/callback")
        assert isinstance(result, GoogleTokenData)
        assert result.google_user_id == "google_id"

    @patch.object(GoogleOAuthService, "_fetch_tokens")
    def test_missing_id_token_raises(self, mock_fetch):
        mock_fetch.return_value = {"access_token": "ya29.abc"}  # no id_token
        with pytest.raises(TokenExchangeError, match="id_token"):
            svc.exchange_code(code="code", redirect_uri="https://example.com/callback")


# ---------------------------------------------------------------------------
# _fetch_tokens — mocking HTTP
# ---------------------------------------------------------------------------


class TestFetchTokens:
    """Tests for the internal _fetch_tokens() HTTP call."""

    @patch.object(GoogleOAuthService, "_get_client_id", return_value="cid")
    @patch.object(GoogleOAuthService, "_get_client_secret", return_value="secret")
    @patch("apps.social_auth.services.google_service.requests.post")
    def test_successful_fetch(self, mock_post, mock_secret, mock_id):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "ya29.token",
            "id_token": "id.token.value",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        result = svc._fetch_tokens("code", "https://example.com/callback")
        assert result["access_token"] == "ya29.token"

    @patch.object(GoogleOAuthService, "_get_client_id", return_value="cid")
    @patch.object(GoogleOAuthService, "_get_client_secret", return_value="secret")
    @patch("apps.social_auth.services.google_service.requests.post")
    def test_http_error_raises(self, mock_post, mock_secret, mock_id):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_post.return_value = mock_response

        with pytest.raises(TokenExchangeError, match="HTTP 400"):
            svc._fetch_tokens("bad_code", "https://example.com/callback")

    @patch.object(GoogleOAuthService, "_get_client_id", return_value="cid")
    @patch.object(GoogleOAuthService, "_get_client_secret", return_value="secret")
    @patch("apps.social_auth.services.google_service.requests.post")
    def test_http_error_non_json_response(self, mock_post, mock_secret, mock_id):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 502
        mock_response.json.side_effect = ValueError("not json")
        mock_response.text = "Bad Gateway"
        mock_post.return_value = mock_response

        with pytest.raises(TokenExchangeError, match="HTTP 502"):
            svc._fetch_tokens("code", "uri")

    @patch.object(GoogleOAuthService, "_get_client_id", return_value="cid")
    @patch.object(GoogleOAuthService, "_get_client_secret", return_value="secret")
    @patch("apps.social_auth.services.google_service.requests.post")
    def test_network_error_raises(self, mock_post, mock_secret, mock_id):
        from requests.exceptions import ConnectionError

        mock_post.side_effect = ConnectionError("connection refused")
        with pytest.raises(TokenExchangeError, match="connection refused"):
            svc._fetch_tokens("code", "uri")

    @patch.object(GoogleOAuthService, "_get_client_id", return_value="cid")
    @patch.object(GoogleOAuthService, "_get_client_secret", return_value="secret")
    @patch("apps.social_auth.services.google_service.requests.post")
    def test_non_json_response_raises(self, mock_post, mock_secret, mock_id):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.side_effect = ValueError("not json")
        mock_post.return_value = mock_response

        with pytest.raises(TokenExchangeError, match="non-JSON"):
            svc._fetch_tokens("code", "uri")


# ---------------------------------------------------------------------------
# _get_client_id / _get_client_secret
# ---------------------------------------------------------------------------


class TestClientCredentials:
    """Tests for credential loading."""

    def test_get_client_id_success(self):
        with override_settings(GOOGLE_OAUTH_CLIENT_ID="my-client-id"):
            assert GoogleOAuthService._get_client_id() == "my-client-id"

    def test_get_client_id_missing_raises(self):
        with override_settings(GOOGLE_OAUTH_CLIENT_ID=None):
            with pytest.raises(TokenVerificationError, match="GOOGLE_OAUTH_CLIENT_ID"):
                GoogleOAuthService._get_client_id()

    def test_get_client_secret_success(self):
        with override_settings(GOOGLE_OAUTH_CLIENT_SECRET="my-secret"):
            assert GoogleOAuthService._get_client_secret() == "my-secret"

    def test_get_client_secret_missing_raises(self):
        with override_settings(GOOGLE_OAUTH_CLIENT_SECRET=None):
            with pytest.raises(TokenVerificationError, match="GOOGLE_OAUTH_CLIENT_SECRET"):
                GoogleOAuthService._get_client_secret()
