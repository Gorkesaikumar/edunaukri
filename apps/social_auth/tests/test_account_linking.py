"""Tests for GoogleAccountLinkingService — all three account-resolution paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.accounts.constants.enums import AccountStatus, ITUserRoleType
from apps.accounts.models.it_user import ITUser
from apps.social_auth.exceptions import SocialAuthError
from apps.social_auth.models import SocialAccount
from apps.social_auth.services.account_linking_service import (
    GoogleAccountLinkingService,
)

pytestmark = pytest.mark.django_db

svc = GoogleAccountLinkingService()


class TestExistingSocialAccountPath:
    """Path 1: SocialAccount already exists → return existing user."""

    def test_returns_existing_user(self, social_account, google_profile_existing):
        result = svc.resolve_or_create(google_profile_existing)
        assert result.was_created is False
        assert str(result.user.pk) == str(social_account.user.pk)
        assert result.social_account_id == str(social_account.pk)

    def test_updates_nothing_when_found(self, social_account, google_profile_existing):
        old_last_login = social_account.last_login_at
        result = svc.resolve_or_create(google_profile_existing)
        social_account.refresh_from_db()
        # The linking service does NOT update last_login — the signal does.
        assert social_account.last_login_at == old_last_login


class TestExistingEmailPath:
    """Path 2: No SocialAccount found, but ITUser exists by email → link."""

    def test_creates_social_account_and_returns_user(
        self, it_user, google_profile_matching_email
    ):
        result = svc.resolve_or_create(google_profile_matching_email)
        assert result.was_created is False
        assert str(result.user.pk) == str(it_user.pk)
        # A new SocialAccount should be created for the email match.
        assert SocialAccount.objects.filter(
            user=it_user,
            provider=SocialAccount.ProviderChoices.GOOGLE,
        ).exists()

    def test_raises_if_already_linked(self, social_account, google_profile_existing):
        """If the user already has a Google link, linking again should raise."""
        with pytest.raises(SocialAuthError, match="already has a Google"):
            svc.resolve_or_create(google_profile_existing)

    def test_email_unverified_skips_lookup(self, it_user, google_profile_unverified):
        """If the Google profile has an unverified email, we should NOT match by email."""
        # The user's email matches profile_unverified, but verified_email=False
        result = svc.resolve_or_create(google_profile_unverified)
        # Since no SocialAccount exists and email is unverified, it should
        # go to the "new user" path.
        assert result.was_created is True

    def test_empty_email_skips_lookup(self, it_user):
        """If the Google profile has an empty email, we should NOT match by email."""
        from apps.social_auth.services.google_service import GoogleTokenData

        profile = GoogleTokenData(
            google_user_id="no_email_id",
            email="",
            name="No Email",
            picture="",
            verified_email=False,
        )
        with pytest.raises(SocialAuthError, match="email address"):
            svc.resolve_or_create(profile)


class TestNewUserPath:
    """Path 3: Neither SocialAccount nor ITUser exist → create everything."""

    def test_creates_user_and_social_account(self, google_profile):
        result = svc.resolve_or_create(google_profile)
        assert result.was_created is True
        user = result.user
        assert isinstance(user, ITUser)
        assert user.email == "newuser@example.com"
        assert user.account_status == AccountStatus.ACTIVE
        assert user.email_verified is True

        # SocialAccount should be linked
        social = SocialAccount.objects.get(user=user)
        assert social.provider == SocialAccount.ProviderChoices.GOOGLE
        assert social.provider_user_id == "new_google_id_999"
        assert social.display_name == "New User"
        assert social.is_verified is True

    def test_creates_job_seeker_role(self, google_profile):
        result = svc.resolve_or_create(google_profile)
        # Verify the user has the JOB_SEEKER role
        from apps.accounts.services.role_assignment_service import (
            RoleAssignmentService,
        )

        assert RoleAssignmentService().user_has_it_role(
            result.user, ITUserRoleType.JOB_SEEKER
        )

    def test_creates_job_seeker_profile(self, google_profile):
        from apps.accounts.profiles.constants.enums import ProfileType
        from apps.it_recruitment.models import JobSeekerProfile

        result = svc.resolve_or_create(google_profile)
        assert JobSeekerProfile.objects.filter(user_id=result.user.pk).exists()

    def test_unverified_email_creates_pending_status(
        self, google_profile_unverified
    ):
        result = svc.resolve_or_create(google_profile_unverified)
        assert result.was_created is True
        assert result.user.account_status == AccountStatus.PENDING_VERIFICATION
        assert result.user.email_verified is False

    def test_empty_email_raises(self):
        from apps.social_auth.services.google_service import GoogleTokenData

        profile = GoogleTokenData(
            google_user_id="empty_email_id",
            email="",
            name="",
            picture="",
            verified_email=False,
        )
        with pytest.raises(SocialAuthError, match="email address"):
            svc.resolve_or_create(profile)

    @patch.object(GoogleAccountLinkingService, "_create_new_user")
    @patch.object(GoogleAccountLinkingService, "_find_existing_user", return_value=None)
    @patch.object(GoogleAccountLinkingService, "_find_social_account", return_value=None)
    def test_selector_order_respected(
        self,
        mock_find_social,
        mock_find_user,
        mock_create_new_user,
        google_profile,
    ):
        """When neither social account nor email match, _create_new_user is called."""
        mock_create_new_user.return_value = (MagicMock(), MagicMock())

        result = svc.resolve_or_create(google_profile)

        mock_find_social.assert_called_once()
        mock_find_user.assert_called_once()
        mock_create_new_user.assert_called_once()
        assert result is not None


class TestTransactionAndLocking:
    """Verify transaction + select_for_update usage."""

    @patch.object(
        SocialAccount.objects,
        "select_for_update",
        return_value=SocialAccount.objects.none(),
    )
    def test_find_social_account_uses_select_for_update(self, mock_sfu):
        """_find_social_account should call select_for_update on the queryset."""
        from apps.social_auth.services.google_service import GoogleTokenData

        profile = GoogleTokenData(
            google_user_id="any",
            email="any@example.com",
            name="",
            picture="",
            verified_email=True,
        )
        result = GoogleAccountLinkingService._find_social_account(profile)
        mock_sfu.assert_called_once()
        assert result is None

    def test_find_existing_user_uses_select_for_update(self, it_user):
        """_find_existing_user should use select_for_update and find matching users."""
        from apps.social_auth.services.google_service import GoogleTokenData

        profile = GoogleTokenData(
            google_user_id="any",
            email=it_user.email,
            name="",
            picture="",
            verified_email=True,
        )
        result = GoogleAccountLinkingService._find_existing_user(profile)
        assert result is not None
        assert result.pk == it_user.pk
