"""Tests for GoogleLoginService — full login flow, JWT attachment."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.social_auth.services.login_service import GoogleLoginResult, GoogleLoginService

pytestmark = pytest.mark.django_db


class TestGoogleLoginService:
    """Tests for GoogleLoginService.login() — orchestrates user resolution,
    session creation, audit logging, signal dispatch, and dashboard URL."""

    def test_login_returns_google_login_result(
        self, mock_request, google_profile, it_user
    ):
        """Verify that login() returns a GoogleLoginResult with correct fields."""
        # Patch the linking, session, audit, signal, and URL services.
        account_linking_patch = patch(
            "apps.social_auth.services.login_service.GoogleAccountLinkingService"
        )
        session_patch = patch(
            "apps.social_auth.services.login_service.SessionService"
        )
        audit_patch = patch(
            "apps.social_auth.services.login_service.AuthAuditService"
        )
        signal_patch = patch(
            "apps.social_auth.services.login_service.social_login_completed"
        )
        portal_patch = patch(
            "apps.social_auth.services.login_service.PortalURLService"
        )

        with account_linking_patch as mock_linking_cls, \
             session_patch as mock_session_cls, \
             audit_patch as mock_audit_cls, \
             signal_patch as mock_signal, \
             portal_patch as mock_portal:

            mock_linking = mock_linking_cls.return_value
            mock_linking.resolve_or_create.return_value = MagicMock(
                user=it_user,
                was_created=True,
                social_account_id="social-account-uuid",
            )

            mock_session = mock_session_cls.return_value

            mock_portal.dashboard_for_user.return_value = "/portal/jobseeker/uuid/dashboard/"

            service = GoogleLoginService()
            result = service.login(mock_request, profile=google_profile)

        assert isinstance(result, GoogleLoginResult)
        assert result.user_id == str(it_user.pk)
        assert result.email == it_user.email
        assert result.was_created is True
        assert result.dashboard_url == "/portal/jobseeker/uuid/dashboard/"
        assert result.user == it_user

        # Verify key collaborators were called.
        mock_linking.resolve_or_create.assert_called_once_with(google_profile)
        mock_session.login_user.assert_called_once_with(
            mock_request, domain="it", user=it_user
        )
        mock_signal.send.assert_called_once()

    def test_login_was_created_false_for_existing_user(
        self, mock_request, google_profile_existing, it_user
    ):
        """When an existing user is resolved, was_created should be False."""
        account_linking_patch = patch(
            "apps.social_auth.services.login_service.GoogleAccountLinkingService"
        )
        session_patch = patch(
            "apps.social_auth.services.login_service.SessionService"
        )
        audit_patch = patch(
            "apps.social_auth.services.login_service.AuthAuditService"
        )
        signal_patch = patch(
            "apps.social_auth.services.login_service.social_login_completed"
        )
        portal_patch = patch(
            "apps.social_auth.services.login_service.PortalURLService"
        )

        with account_linking_patch as mock_linking_cls, \
             session_patch as mock_session_cls, \
             audit_patch as mock_audit_cls, \
             signal_patch as mock_signal, \
             portal_patch as mock_portal:

            mock_linking = mock_linking_cls.return_value
            mock_linking.resolve_or_create.return_value = MagicMock(
                user=it_user,
                was_created=False,
                social_account_id="existing-uuid",
            )

            mock_portal.dashboard_for_user.return_value = "/portal/jobseeker/uuid/dashboard/"

            service = GoogleLoginService()
            result = service.login(mock_request, profile=google_profile_existing)

        assert result.was_created is False

    def test_attach_jwt_delegates_to_web_jwt_service(self):
        """Verify attach_jwt() calls WebJWTService.attach_tokens_with_request."""
        mock_response = MagicMock()
        mock_user = MagicMock()
        mock_request = MagicMock()

        with patch(
            "apps.social_auth.services.login_service.WebJWTService"
        ) as mock_jwt_cls:
            mock_jwt = mock_jwt_cls.return_value

            GoogleLoginService.attach_jwt(
                mock_response,
                user=mock_user,
                request=mock_request,
            )

            mock_jwt.attach_tokens_with_request.assert_called_once_with(
                mock_response,
                user=mock_user,
                domain="it",
                request=mock_request,
                auth_method="google",
            )

    def test_dispatch_signal_sends_social_login_completed(self):
        """Verify _dispatch_signal sends the correct signal."""
        mock_user = MagicMock()
        with patch(
            "apps.social_auth.services.login_service.social_login_completed"
        ) as mock_signal:
            GoogleLoginService._dispatch_signal(
                user=mock_user,
                social_account_id="uuid",
                provider="google",
                profile=None,
            )
            mock_signal.send.assert_called_once_with(
                sender=GoogleLoginService,
                user=mock_user,
                social_account_id="uuid",
                provider="google",
                profile=None,
            )


class TestExtractMeta:
    """Test the _extract_meta helper function."""

    def test_extracts_ip_and_user_agent(self, mock_request):
        from apps.social_auth.services.login_service import _extract_meta

        meta = _extract_meta(mock_request)
        assert meta["ip_address"] == "127.0.0.1"
        assert meta["user_agent"] == "test-agent/1.0"

    def test_returns_empty_dict_for_none_request(self):
        from apps.social_auth.services.login_service import _extract_meta

        meta = _extract_meta(None)
        assert meta == {}
