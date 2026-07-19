"""Tests for selectors — all read-side queries."""

from __future__ import annotations

import pytest

from apps.social_auth.selectors import (
    get_social_accounts_for_user,
    get_social_account_by_provider,
    resolve_user_by_provider,
    provider_is_linked,
)

pytestmark = pytest.mark.django_db


class TestGetSocialAccountsForUser:
    def test_returns_accounts(self, social_account):
        accounts = list(get_social_accounts_for_user(social_account.user))
        assert len(accounts) == 1
        assert accounts[0].provider == "google"

    def test_returns_empty_queryset(self, it_user):
        accounts = list(get_social_accounts_for_user(it_user))
        assert accounts == []


class TestGetSocialAccountByProvider:
    def test_found(self, social_account):
        account = get_social_account_by_provider(
            social_account.user, provider="google"
        )
        assert account is not None
        assert account.provider == "google"

    def test_not_found(self, it_user):
        account = get_social_account_by_provider(it_user, provider="linkedin")
        assert account is None


class TestResolveUserByProvider:
    def test_resolves_user(self, social_account):
        user = resolve_user_by_provider(
            provider="google",
            provider_user_id="google_user_12345",
        )
        assert user is not None
        assert user.email == "test@example.com"

    def test_returns_none_if_not_found(self):
        user = resolve_user_by_provider(
            provider="google",
            provider_user_id="nonexistent",
        )
        assert user is None


class TestProviderIsLinked:
    def test_returns_true(self, social_account):
        assert provider_is_linked(social_account.user, "google") is True

    def test_returns_false(self, it_user):
        assert provider_is_linked(it_user, "linkedin") is False
