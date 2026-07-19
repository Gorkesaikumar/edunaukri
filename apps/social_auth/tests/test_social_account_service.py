"""Tests for SocialAccountService — CRUD, duplicate prevention, disconnect."""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.social_auth.exceptions import (
    AccountAlreadyLinkedError,
    ProviderNotSupportedError,
    SocialAuthError,
)
from apps.social_auth.models import SocialAccount
from apps.social_auth.services.social_account_service import (
    SocialAccountResult,
    SocialAccountService,
)

pytestmark = pytest.mark.django_db

svc = SocialAccountService()


class TestFindAndRead:
    """Test get_by_id, get_by_provider, get_for_user, resolve_user."""

    def test_get_by_id_returns_account(self, social_account):
        result = svc.get_by_id(str(social_account.pk))
        assert result is not None
        assert result.id == str(social_account.pk)
        assert result.email == "test@example.com"

    def test_get_by_id_returns_none_when_missing(self):
        result = svc.get_by_id("00000000-0000-0000-0000-000000000000")
        assert result is None

    def test_get_by_provider_found(self, social_account):
        result = svc.get_by_provider(
            provider="google",
            provider_user_id="google_user_12345",
        )
        assert result is not None
        assert result.email == "test@example.com"

    def test_get_by_provider_not_found(self):
        result = svc.get_by_provider(
            provider="google",
            provider_user_id="nonexistent",
        )
        assert result is None

    def test_get_for_user_returns_accounts(self, social_account, it_user):
        results = svc.get_for_user(it_user)
        assert results.total_count == 1
        assert results.accounts[0].provider == "google"

    def test_get_for_user_returns_empty_list(self, it_user):
        results = svc.get_for_user(it_user)
        assert results.total_count == 0
        assert results.accounts == []

    def test_get_by_provider_for_user(self, social_account, it_user):
        result = svc.get_by_provider_for_user(it_user, provider="google")
        assert result is not None
        assert result.provider == "google"

    def test_get_by_provider_for_user_wrong_provider(self, social_account, it_user):
        result = svc.get_by_provider_for_user(it_user, provider="linkedin")
        assert result is None

    def test_resolve_user_returns_user(self, social_account):
        user = svc.resolve_user(
            provider="google",
            provider_user_id="google_user_12345",
        )
        assert user is not None
        assert user.email == "test@example.com"

    def test_resolve_user_returns_none(self):
        user = svc.resolve_user(
            provider="google",
            provider_user_id="no_such_id",
        )
        assert user is None


class TestCreate:
    """Test the create() method — success, duplicates, unsupported providers."""

    def test_create_success(self, it_user):
        result = svc.create(
            user=it_user,
            provider="google",
            provider_user_id="new_google_id",
            email="new@example.com",
            display_name="New User",
            profile_picture="https://example.com/pic.jpg",
            is_verified=True,
        )
        assert result.provider == "google"
        assert result.email == "new@example.com"
        assert result.user_id == str(it_user.pk)

    def test_create_unsupported_provider_raises(self, it_user):
        with pytest.raises(ProviderNotSupportedError):
            svc.create(
                user=it_user,
                provider="unknown_provider",
                provider_user_id="x",
            )

    def test_create_duplicate_identity_raises(self, social_account, it_user):
        """Same provider + provider_user_id for a different user should raise."""
        from apps.accounts.models.it_user import ITUser

        other = ITUser.objects.create(
            email="other@example.com",
            email_verified=True,
        )
        with pytest.raises(AccountAlreadyLinkedError):
            svc.create(
                user=other,
                provider="google",
                provider_user_id="google_user_12345",
            )

    def test_create_already_linked_for_user_raises(self, social_account, it_user):
        """Same user + same provider should raise."""
        with pytest.raises(SocialAuthError, match="already linked"):
            svc.create(
                user=it_user,
                provider="google",
                provider_user_id="another_id",
            )


class TestLinkAccount:
    """Test link_account() — idempotency and cross-user protection."""

    def test_link_new_provider_creates(self, it_user):
        result = svc.link_account(
            user=it_user,
            provider="linkedin",
            provider_user_id="linkedin_id",
            email="test@example.com",
        )
        assert result.was_created is True
        assert result.account.provider == "linkedin"

    def test_link_existing_is_idempotent(self, social_account, it_user):
        result = svc.link_account(
            user=it_user,
            provider="google",
            provider_user_id="google_user_12345",
        )
        assert result.was_created is False
        assert "already linked" in result.message

    def test_link_claimed_by_other_raises(self, social_account, another_user):
        with pytest.raises(AccountAlreadyLinkedError):
            svc.link_account(
                user=another_user,
                provider="google",
                provider_user_id="google_user_12345",
            )


class TestDuplicateCheck:
    """Test check_duplicate() — cross-user and same-user scenarios."""

    def test_check_duplicate_found_cross_user(self, social_account):
        result = svc.check_duplicate(
            provider="google",
            provider_user_id="google_user_12345",
        )
        assert result.is_duplicate is True
        assert result.existing_account is not None

    def test_check_duplicate_not_found(self):
        result = svc.check_duplicate(
            provider="google",
            provider_user_id="nonexistent",
        )
        assert result.is_duplicate is False

    def test_check_duplicate_same_user_already_linked(self, social_account, it_user):
        result = svc.check_duplicate(
            provider="google",
            provider_user_id="any_other_id",
            user=it_user,
        )
        assert result.is_duplicate is True
        assert "already linked" in result.detail


class TestUpdateMethods:
    """Test update_profile_picture, update_display_name, update_last_login."""

    def test_update_profile_picture(self, social_account):
        result = svc.update_profile_picture(
            str(social_account.pk),
            profile_picture="https://new-pic.com/avatar.jpg",
        )
        assert result.profile_picture == "https://new-pic.com/avatar.jpg"

    def test_update_profile_picture_not_found(self):
        with pytest.raises(SocialAuthError):
            svc.update_profile_picture(
                "00000000-0000-0000-0000-000000000000",
                profile_picture="https://pic.com/a.jpg",
            )

    def test_update_display_name(self, social_account):
        result = svc.update_display_name(
            str(social_account.pk),
            display_name="Updated Name",
        )
        assert result.display_name == "Updated Name"

    def test_update_last_login_defaults_to_now(self, social_account):
        result = svc.update_last_login(str(social_account.pk))
        assert result.last_login_at is not None

    def test_update_last_login_with_explicit_time(self, social_account):
        when = timezone.now()
        result = svc.update_last_login(
            str(social_account.pk),
            last_login_at=when,
        )
        assert result.last_login_at == when.isoformat()


class TestDeleteAndDisconnect:
    """Test delete_account() and disconnect_provider()."""

    def test_delete_account_removes_record(self, social_account):
        pk = str(social_account.pk)
        svc.delete_account(pk)
        assert SocialAccount.objects.filter(pk=pk).exists() is False

    def test_delete_account_not_found_raises(self):
        with pytest.raises(SocialAuthError):
            svc.delete_account("00000000-0000-0000-0000-000000000000")

    def test_disconnect_provider_removes(self, social_account, it_user):
        svc.disconnect_provider(it_user, provider="google")
        assert (
            SocialAccount.objects.filter(user=it_user, provider="google").exists()
            is False
        )

    def test_disconnect_provider_not_linked_raises(self, it_user):
        with pytest.raises(SocialAuthError, match="No linkedin account"):
            svc.disconnect_provider(it_user, provider="linkedin")


class TestSocialAccountResult:
    """Test the SocialAccountResult dataclass."""

    def test_from_model(self, social_account):
        result = SocialAccountResult.from_model(social_account)
        assert result.id == str(social_account.pk)
        assert result.provider == "google"
        assert result.last_login_at is not None  # was set in fixture

    def test_from_model_none_last_login(self, it_user):
        account = SocialAccount.objects.create(
            user=it_user,
            provider="linkedin",
            provider_user_id="li_id",
        )
        result = SocialAccountResult.from_model(account)
        assert result.last_login_at is None
