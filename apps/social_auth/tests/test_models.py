"""Tests for the SocialAccount model — __str__, token helpers, constraints."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.social_auth.models import SocialAccount

pytestmark = pytest.mark.django_db


class TestSocialAccountModel:
    """Model-level tests: string representation, token helpers, uniqueness."""

    def test_str_uses_provider_and_email(self, social_account):
        """__str__ should show the provider display name and email."""
        text = str(social_account)
        assert "Google" in text
        assert "test@example.com" in text

    def test_str_falls_back_to_provider_user_id(self, social_account):
        """If email is blank, __str__ should show provider_user_id."""
        social_account.email = ""
        social_account.save(update_fields=["email"])
        text = str(social_account)
        assert "Google" in text
        assert "google_user_12345" in text

    def test_update_tokens_sets_access_token(self, social_account):
        """update_tokens() should persist the new access token."""
        social_account.update_tokens(access_token="new_access_456")
        social_account.refresh_from_db()
        assert social_account.access_token == "new_access_456"

    def test_update_tokens_sets_refresh_token(self, social_account):
        """update_tokens() should persist the new refresh token."""
        social_account.update_tokens(refresh_token="new_refresh_789")
        social_account.refresh_from_db()
        assert social_account.refresh_token == "new_refresh_789"

    def test_update_tokens_sets_expiry(self, social_account):
        """update_tokens() should persist the token expiry."""
        expiry = timezone.now() + timedelta(hours=1)
        social_account.update_tokens(token_expiry=expiry)
        social_account.refresh_from_db()
        assert social_account.token_expiry == expiry

    def test_update_tokens_updates_updated_at(self, social_account):
        """update_tokens() should bump the updated_at timestamp."""
        old = social_account.updated_at
        social_account.update_tokens(access_token="tok")
        social_account.refresh_from_db()
        assert social_account.updated_at >= old

    def test_is_token_valid_returns_false_when_none(self, social_account):
        """is_token_valid() should return False when token_expiry is None."""
        social_account.token_expiry = None
        assert social_account.is_token_valid() is False

    def test_is_token_valid_returns_false_when_expired(self, social_account):
        """is_token_valid() should return False when the token has expired."""
        social_account.token_expiry = timezone.now() - timedelta(seconds=1)
        assert social_account.is_token_valid() is False

    def test_is_token_valid_returns_true_when_valid(self, social_account):
        """is_token_valid() should return True when the token is still valid."""
        social_account.token_expiry = timezone.now() + timedelta(hours=1)
        assert social_account.is_token_valid() is True

    # ------------------------------------------------------------------
    # Constraint: uq_social_auth_provider_identity
    # ------------------------------------------------------------------

    def test_duplicate_provider_user_id_raises(self, social_account, it_user):
        """The same provider+provider_user_id should not be linkable to another user."""
        with pytest.raises(IntegrityError):
            SocialAccount.objects.create(
                user=it_user,
                provider=SocialAccount.ProviderChoices.GOOGLE,
                provider_user_id=social_account.provider_user_id,
                email="another@example.com",
            )

    # ------------------------------------------------------------------
    # Constraint: uq_social_auth_one_per_provider_per_user
    # ------------------------------------------------------------------

    def test_duplicate_provider_for_user_raises(self, social_account):
        """The same user should not be able to link the same provider twice."""
        with pytest.raises(IntegrityError):
            SocialAccount.objects.create(
                user=social_account.user,
                provider=SocialAccount.ProviderChoices.GOOGLE,
                provider_user_id="different_provider_id",
                email="test@example.com",
            )

    def test_different_provider_for_user_succeeds(self, social_account):
        """A user can link a different provider (e.g. LinkedIn + Google)."""
        account = SocialAccount.objects.create(
            user=social_account.user,
            provider=SocialAccount.ProviderChoices.LINKEDIN,
            provider_user_id="linkedin_id",
            email="test@example.com",
        )
        assert account.pk is not None
        assert account.provider == SocialAccount.ProviderChoices.LINKEDIN

    # ------------------------------------------------------------------
    # ordering
    # ------------------------------------------------------------------

    def test_default_ordering_is_newest_first(self, social_account, it_user):
        """Default ordering should be '-created_at'."""
        older = social_account.created_at
        newer_account = SocialAccount.objects.create(
            user=it_user,
            provider=SocialAccount.ProviderChoices.LINKEDIN,
            provider_user_id="linkedin_only",
            email="test@example.com",
        )
        qs = SocialAccount.objects.all()
        # The newest should come first.
        assert qs.first() == newer_account
