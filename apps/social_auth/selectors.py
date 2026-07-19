"""
Social Auth — selectors
Read-side optimized queries. No writes.
"""

from __future__ import annotations

from django.db.models import QuerySet

from apps.social_auth.models import SocialAccount


def get_social_accounts_for_user(user) -> QuerySet[SocialAccount]:
    """Return all social accounts linked to a given user."""
    return SocialAccount.filter_by_user(user)


def get_social_account_by_provider(
    user, provider: str,
) -> SocialAccount | None:
    """Return a single social account for a given user and provider."""
    return SocialAccount.for_user_by_provider(user, provider)


def resolve_user_by_provider(
    provider: str, provider_user_id: str,
):
    """Look up a local user by their social provider ID."""
    return SocialAccount.resolve_user(
        provider=provider,
        provider_user_id=provider_user_id,
    )


def provider_is_linked(user, provider: str) -> bool:
    """Check whether a user has already linked a given provider."""
    return SocialAccount.exists_for_user_and_provider(user, provider)
