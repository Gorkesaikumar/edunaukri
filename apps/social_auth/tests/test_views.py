"""Tests for views — GoogleLoginView and GoogleCallbackView integration tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.social_auth.exceptions import SocialAuthError, TokenExchangeError

pytestmark = pytest.mark.django_db

LOGIN_URL = reverse("social_auth:google-login")
CALLBACK_URL = reverse("social_auth:google-callback")


class TestGoogleLoginView:
    """POST /auth/google/login/"""

    def test_returns_authorize_url(self):
        client = APIClient()
        with patch(
            "apps.social_auth.views.GoogleOAuthService"
        ) as mock_svc_cls, \
             patch(
            "apps.social_auth.views.google_redirect_uri"
        ) as mock_uri:
            mock_uri.return_value = "https://example.com/api/social-auth/google/callback/"
            mock_svc = mock_svc_cls.return_value
            mock_svc.get_authorization_url.return_value = type(
                "Result", (),
                {"authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
                 "state": "csrf_state_abc"}
            )()

            response = client.post(
                LOGIN_URL,
                {},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert "authorize_url" in response.json()
        assert "state" in response.json()

    def test_empty_body_returns_200(self):
        """Login no longer requires redirect_uri — empty body is valid."""
        client = APIClient()
        with patch(
            "apps.social_auth.views.GoogleOAuthService"
        ) as mock_svc_cls, \
             patch(
            "apps.social_auth.views.google_redirect_uri"
        ) as mock_uri:
            mock_uri.return_value = "https://example.com/api/social-auth/google/callback/"
            mock_svc = mock_svc_cls.return_value
            mock_svc.get_authorization_url.return_value = type(
                "Result", (),
                {"authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
                 "state": ""}
            )()

            response = client.post(
                LOGIN_URL,
                {},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK


class TestGoogleCallbackView:
    """POST /auth/google/callback/"""

    def test_successful_login_returns_user_data(self, it_user):
        client = APIClient()
        with patch(
            "apps.social_auth.views.GoogleOAuthService"
        ) as mock_oauth_cls, \
             patch(
            "apps.social_auth.views.GoogleLoginService"
        ) as mock_login_cls, \
             patch(
            "apps.social_auth.views.google_redirect_uri"
        ) as mock_uri:
            mock_uri.return_value = "https://example.com/api/social-auth/google/callback/"

            # Mock OAuth service
            mock_oauth = mock_oauth_cls.return_value
            mock_oauth.exchange_code.return_value = type(
                "TokenData", (),
                {"google_user_id": "id", "email": "test@example.com",
                 "name": "Test", "picture": "", "verified_email": True}
            )()

            # Mock login service
            mock_login = mock_login_cls.return_value
            mock_login_result = type(
                "Result", (),
                {"user_id": str(it_user.pk), "email": "test@example.com",
                 "was_created": False, "dashboard_url": "/portal/dashboard/",
                 "user": it_user}
            )()
            mock_login.login.return_value = mock_login_result

            response = client.post(
                CALLBACK_URL,
                {"code": "valid_code"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(it_user.pk)
        assert data["email"] == "test@example.com"
        assert data["was_created"] is False
        assert data["dashboard_url"] == "/portal/dashboard/"

    def test_social_auth_error_returns_400(self):
        client = APIClient()
        with patch(
            "apps.social_auth.views.GoogleOAuthService"
        ) as mock_oauth_cls, \
             patch(
            "apps.social_auth.views.google_redirect_uri"
        ) as mock_uri:
            mock_uri.return_value = "https://example.com/api/social-auth/google/callback/"
            mock_oauth = mock_oauth_cls.return_value
            mock_oauth.exchange_code.side_effect = TokenExchangeError(
                "google", "invalid code"
            )

            response = client.post(
                CALLBACK_URL,
                {"code": "bad"},
                format="json",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "code" in data
        assert data["code"] == "TokenExchangeError"

    def test_unexpected_error_returns_500(self):
        client = APIClient()
        with patch(
            "apps.social_auth.views.GoogleOAuthService"
        ) as mock_oauth_cls, \
             patch(
            "apps.social_auth.views.google_redirect_uri"
        ) as mock_uri:
            mock_uri.return_value = "https://example.com/api/social-auth/google/callback/"
            mock_oauth = mock_oauth_cls.return_value
            mock_oauth.exchange_code.side_effect = RuntimeError("unexpected")

            response = client.post(
                CALLBACK_URL,
                {"code": "bad"},
                format="json",
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "try again" in response.json()["error"].lower()

    def test_missing_code_returns_400(self):
        client = APIClient()
        response = client.post(
            CALLBACK_URL,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
