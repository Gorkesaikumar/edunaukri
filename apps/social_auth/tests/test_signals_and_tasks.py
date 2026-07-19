"""Tests for signals and Celery task — social_login_completed handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.social_auth.models import SocialAccount
from apps.social_auth.signals import (
    queue_login_notification,
    social_login_completed,
    sync_provider_profile,
    update_login_fields,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Signal: update_login_fields
# ---------------------------------------------------------------------------


class TestUpdateLoginFields:
    """update_login_fields handler should set last_login_at on the SocialAccount."""

    def test_updates_last_login(self, social_account):
        old = social_account.last_login_at
        social_login_completed.send(
            sender="test",
            user=social_account.user,
            social_account_id=str(social_account.pk),
            provider="google",
            profile=None,
        )
        social_account.refresh_from_db()
        assert social_account.last_login_at >= old

    def test_skips_when_no_social_account_id(self):
        """Handler should silently return if social_account_id is missing."""
        # Should not raise.
        social_login_completed.send(
            sender="test",
            user="whatever",
            social_account_id=None,
            provider="google",
        )

    def test_logs_exception_on_failure(self, caplog):
        """If the update fails, the handler should log an exception."""
        with patch(
            "apps.social_auth.signals.SocialAccount.objects.filter",
            side_effect=Exception("DB error"),
        ):
            social_login_completed.send(
                sender="test",
                user=MagicMock(),
                social_account_id="some-uuid",
                provider="google",
                profile=None,
            )
        assert any(
            "Failed to update last_login" in msg for msg in caplog.messages
        )


# ---------------------------------------------------------------------------
# Signal: sync_provider_profile
# ---------------------------------------------------------------------------


class TestSyncProviderProfile:
    """sync_provider_profile handler should update display_name and profile_picture."""

    def test_does_nothing_without_profile(self, social_account):
        """When no profile kwarg is provided, the handler should be a no-op."""
        old_name = social_account.display_name
        old_pic = social_account.profile_picture
        sync_provider_profile(
            sender="test",
            user=social_account.user,
            social_account_id=str(social_account.pk),
            provider="google",
            profile=None,
        )
        social_account.refresh_from_db()
        assert social_account.display_name == old_name
        assert social_account.profile_picture == old_pic

    def test_updates_profile_when_profile_provided(self, social_account):
        """When a profile with name/picture is provided, update the account."""
        profile = MagicMock()
        profile.name = "Updated Name"
        profile.picture = "https://new-pic.com/avatar.jpg"

        sync_provider_profile(
            sender="test",
            user=social_account.user,
            social_account_id=str(social_account.pk),
            provider="google",
            profile=profile,
        )
        social_account.refresh_from_db()
        assert social_account.display_name == "Updated Name"
        assert social_account.profile_picture == "https://new-pic.com/avatar.jpg"

    def test_skips_without_social_account_id(self):
        """Handler should silently return if social_account_id is missing."""
        # Should not raise.
        sync_provider_profile(
            sender="test",
            user=MagicMock(),
            social_account_id=None,
            provider="google",
        )

    def test_logs_exception_on_failure(self, caplog):
        """If the update fails, the handler should log an exception."""
        profile = MagicMock()
        profile.name = "Name"
        profile.picture = "https://pic.com/a.jpg"

        with patch(
            "apps.social_auth.signals.SocialAccount.objects.filter",
            side_effect=Exception("DB error"),
        ):
            sync_provider_profile(
                sender="test",
                user=MagicMock(),
                social_account_id="some-uuid",
                provider="google",
                profile=profile,
            )
        assert any(
            "Failed to sync provider profile" in msg for msg in caplog.messages
        )


# ---------------------------------------------------------------------------
# Signal: queue_login_notification
# ---------------------------------------------------------------------------


class TestQueueLoginNotification:
    """queue_login_notification handler should dispatch the Celery task."""

    @patch("apps.social_auth.signals.create_social_login_notification_task")
    def test_dispatches_task(self, mock_task, it_user, social_account):
        queue_login_notification(
            sender="test",
            user=it_user,
            social_account_id=str(social_account.pk),
            provider="google",
        )
        mock_task.delay.assert_called_once_with(
            user_id=str(it_user.pk),
            provider="google",
            social_account_id=str(social_account.pk),
        )

    @patch("apps.social_auth.signals.create_social_login_notification_task")
    def test_handles_task_exception_gracefully(self, mock_task, caplog):
        """If the task.delay() call fails, handler should log and not crash."""
        mock_task.delay.side_effect = RuntimeError("broker down")

        # Should not raise.
        queue_login_notification(
            sender="test",
            user=MagicMock(pk="user-uuid"),
            social_account_id="social-uuid",
            provider="google",
        )
        assert any(
            "Failed to queue social login" in msg for msg in caplog.messages
        )


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


class TestCreateSocialLoginNotificationTask:
    """Test the Celery task directly."""

    def test_creates_notification(self, it_user, social_account):
        from apps.social_auth.tasks import create_social_login_notification_task
        from apps.notifications.models import Notification

        result = create_social_login_notification_task(
            None,  # self
            user_id=str(it_user.pk),
            provider="google",
            social_account_id=str(social_account.pk),
        )

        assert result["user_id"] == str(it_user.pk)
        assert result["provider"] == "google"
        assert result["notification_id"] is not None

        notif = Notification.objects.get(pk=result["notification_id"])
        assert notif.recipient_domain == "it"
        assert notif.title == "Signed in with Google"
        assert "google" in notif.body.lower()

    def test_creates_notification_with_unknown_provider(self, it_user):
        from apps.social_auth.tasks import create_social_login_notification_task
        from apps.notifications.models import Notification

        result = create_social_login_notification_task(
            None,
            user_id=str(it_user.pk),
            provider="",
            social_account_id="",
        )

        notif = Notification.objects.get(pk=result["notification_id"])
        assert "Social" in notif.title  # Falls back to "Social"
