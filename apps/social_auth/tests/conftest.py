"""Shared fixtures for social_auth tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.it_user import ITUser
from apps.social_auth.models import SocialAccount
from apps.social_auth.services.google_service import GoogleTokenData


# ---------------------------------------------------------------------------
# Fixtures: Model instances
# ---------------------------------------------------------------------------


@pytest.fixture
def it_user(db):
    """Create a minimal, active ITUser for testing.

    The user has a verified email and an unusable (OAuth-only) password.
    """
    user = ITUser.objects.create(
        email="test@example.com",
        account_status=AccountStatus.ACTIVE,
        email_verified=True,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def another_user(db):
    """A second ITUser — useful for duplicate / cross-user scenarios."""
    user = ITUser.objects.create(
        email="other@example.com",
        account_status=AccountStatus.ACTIVE,
        email_verified=True,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def social_account(db, it_user):
    """A SocialAccount already linked to *it_user* via Google."""
    return SocialAccount.objects.create(
        user=it_user,
        user_domain=it_user.domain,
        provider=SocialAccount.ProviderChoices.GOOGLE,
        provider_user_id="google_user_12345",
        email="test@example.com",
        display_name="Test User",
        profile_picture="https://example.com/pic.jpg",
        is_verified=True,
        last_login_at=timezone.now(),
    )


# ---------------------------------------------------------------------------
# Fixtures: Value objects
# ---------------------------------------------------------------------------


@pytest.fixture
def google_profile() -> GoogleTokenData:
    """A verified Google profile for a brand-new user (no existing account)."""
    return GoogleTokenData(
        google_user_id="new_google_id_999",
        email="newuser@example.com",
        name="New User",
        picture="https://example.com/new_pic.jpg",
        verified_email=True,
    )


@pytest.fixture
def google_profile_unverified() -> GoogleTokenData:
    """A Google profile with an unverified email."""
    return GoogleTokenData(
        google_user_id="unverified_google_id",
        email="unverified@example.com",
        name="Unverified User",
        picture="",
        verified_email=False,
    )


@pytest.fixture
def google_profile_existing() -> GoogleTokenData:
    """A Google profile that matches the *social_account* fixture."""
    return GoogleTokenData(
        google_user_id="google_user_12345",
        email="test@example.com",
        name="Test User",
        picture="https://example.com/pic.jpg",
        verified_email=True,
    )


@pytest.fixture
def google_profile_matching_email(google_profile_existing):
    """A Google profile with a different google_user_id but the same email as *it_user*."""
    # Keep email = "test@example.com" but change the google_user_id so it
    # won't match by social identity — it will match by email instead.
    return GoogleTokenData(
        google_user_id="different_google_id",
        email="test@example.com",
        name="Test User",
        picture="https://example.com/pic.jpg",
        verified_email=True,
    )


# ---------------------------------------------------------------------------
# Fixtures: Mock request
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_request():
    """A bare-minimum Django HttpRequest mocked for service calls."""
    request = MagicMock()
    request.META = {
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_USER_AGENT": "test-agent/1.0",
    }
    request.session = {}
    return request
