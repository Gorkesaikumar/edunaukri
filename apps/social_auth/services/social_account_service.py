"""Social account service — find, create, link, update, and disconnect social accounts."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.core.services.base import BaseService
from apps.social_auth.exceptions import (
    AccountAlreadyLinkedError,
    ProviderNotSupportedError,
    SocialAuthError,
)
from apps.social_auth.models import SocialAccount


# ---------------------------------------------------------------------------
# Strongly-typed result objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SocialAccountResult:
    """Public representation of a social account returned by the service."""

    id: str
    user_id: str
    user_domain: str
    provider: str
    provider_user_id: str
    email: str
    display_name: str
    profile_picture: str
    is_verified: bool
    last_login_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, account: SocialAccount) -> SocialAccountResult:
        return cls(
            id=str(account.id),
            user_id=str(account.object_id),
            user_domain=account.user_domain,
            provider=account.provider,
            provider_user_id=account.provider_user_id,
            email=account.email,
            display_name=account.display_name,
            profile_picture=account.profile_picture,
            is_verified=account.is_verified,
            last_login_at=(
                account.last_login_at.isoformat()
                if account.last_login_at
                else None
            ),
            created_at=account.created_at.isoformat(),
            updated_at=account.updated_at.isoformat(),
        )


@dataclass(frozen=True)
class SocialAccountListResult:
    """Paginated or list result for a user's linked social accounts."""

    accounts: list[SocialAccountResult] = field(default_factory=list)
    total_count: int = 0


@dataclass(frozen=True)
class LinkAccountResult:
    """Result of linking a social provider to a user."""

    account: SocialAccountResult
    was_created: bool
    message: str


@dataclass(frozen=True)
class DuplicateCheckResult:
    """Result of a duplicate check."""

    is_duplicate: bool
    existing_account: SocialAccountResult | None
    detail: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SocialAccountService(BaseService):
    """Orchestrates the creation, linking, update, and removal of social accounts.

    All ORM access is encapsulated here. Views must never call
    ``SocialAccount.objects`` directly.
    """

    # ------------------------------------------------------------------
    # Find / Read
    # ------------------------------------------------------------------

    def get_by_id(self, account_id: str) -> SocialAccountResult | None:
        """Retrieve a social account by its UUID."""
        account = SocialAccount.objects.filter(pk=account_id).first()
        return SocialAccountResult.from_model(account) if account else None

    def get_by_provider(
        self,
        *,
        provider: str,
        provider_user_id: str,
    ) -> SocialAccountResult | None:
        """Find a social account by provider and the provider's user ID."""
        account = SocialAccount.objects.filter(
            provider=provider,
            provider_user_id=provider_user_id,
        ).first()
        return SocialAccountResult.from_model(account) if account else None

    def get_for_user(
        self,
        user,
    ) -> SocialAccountListResult:
        """Return every social account linked to the given user."""
        accounts = list(
            SocialAccount.filter_by_user(user).order_by("-created_at")
        )
        return SocialAccountListResult(
            accounts=[SocialAccountResult.from_model(a) for a in accounts],
            total_count=len(accounts),
        )

    def get_by_provider_for_user(
        self,
        user,
        *,
        provider: str,
    ) -> SocialAccountResult | None:
        """Return a single social account for a user+provider combination."""
        account = SocialAccount.for_user_by_provider(user, provider)
        return SocialAccountResult.from_model(account) if account else None

    def resolve_user(
        self,
        *,
        provider: str,
        provider_user_id: str,
    ):
        """Resolve the local user linked to a given social identity.

        Returns the user instance (or ``None``) so callers can authenticate
        without an extra query.
        """
        return SocialAccount.resolve_user(
            provider=provider,
            provider_user_id=provider_user_id,
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    @BaseService.atomic
    def create(
        self,
        *,
        user,
        provider: str,
        provider_user_id: str,
        email: str = "",
        display_name: str = "",
        profile_picture: str = "",
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: datetime.datetime | None = None,
        is_verified: bool = False,
    ) -> SocialAccountResult:
        """Create a new social account and link it to a local user.

        Raises:
            ProviderNotSupportedError: If *provider* is unknown.
            AccountAlreadyLinkedError: If the social identity is already
                linked to *another* local user.
        """
        self._validate_provider(provider)
        self._raise_if_claimed_by_other(provider, provider_user_id)
        self._raise_if_already_linked(user, provider)

        account = SocialAccount.create_for_user(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            display_name=display_name,
            profile_picture=profile_picture,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            is_verified=is_verified,
            last_login_at=timezone.now(),
        )
        return SocialAccountResult.from_model(account)

    # ------------------------------------------------------------------
    # Link provider to existing user (idempotent)
    # ------------------------------------------------------------------

    @BaseService.atomic
    def link_account(
        self,
        *,
        user,
        provider: str,
        provider_user_id: str,
        email: str = "",
        display_name: str = "",
        profile_picture: str = "",
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: datetime.datetime | None = None,
        is_verified: bool = False,
    ) -> LinkAccountResult:
        """Link a social provider to a local user.

        If the account already exists it is returned as-is (idempotent).
        If the same social identity is linked to a *different* user,
        ``AccountAlreadyLinkedError`` is raised.

        Returns:
            LinkAccountResult with ``was_created`` indicating whether a new
            row was inserted.
        """
        self._validate_provider(provider)
        self._raise_if_claimed_by_other(provider, provider_user_id, exclude_user=user)

        existing = SocialAccount.for_user_by_provider(user, provider)

        if existing:
            return LinkAccountResult(
                account=SocialAccountResult.from_model(existing),
                was_created=False,
                message=f"{provider} account is already linked.",
            )

        account = SocialAccount.create_for_user(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            display_name=display_name,
            profile_picture=profile_picture,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            is_verified=is_verified,
            last_login_at=timezone.now(),
        )
        return LinkAccountResult(
            account=SocialAccountResult.from_model(account),
            was_created=True,
            message=f"{provider} account linked successfully.",
        )

    # ------------------------------------------------------------------
    # Duplicate check
    # ------------------------------------------------------------------

    def check_duplicate(
        self,
        *,
        provider: str,
        provider_user_id: str,
        user=None,
    ) -> DuplicateCheckResult:
        """Check whether a social identity would be a duplicate.

        Args:
            provider: OAuth provider name.
            provider_user_id: Unique user ID from the provider.
            user: Optional — if provided, also checks whether this user
                has already linked the given provider.

        Returns:
            ``DuplicateCheckResult`` describing what (if anything) conflicts.
        """
        self._validate_provider(provider)

        # Check if the social identity is already linked to someone.
        existing = SocialAccount.objects.filter(
            provider=provider,
            provider_user_id=provider_user_id,
        ).first()

        if existing:
            return DuplicateCheckResult(
                is_duplicate=True,
                existing_account=SocialAccountResult.from_model(existing),
                detail=(
                    f"This {provider} account is already linked to another user."
                ),
            )

        # Check if this user already linked this provider.
        if user is not None:
            already_linked = SocialAccount.exists_for_user_and_provider(user, provider)
            if already_linked:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    existing_account=None,
                    detail=f"You have already linked a {provider} account.",
                )

        return DuplicateCheckResult(
            is_duplicate=False,
            existing_account=None,
            detail="No duplicate found.",
        )

    # ------------------------------------------------------------------
    # Update profile picture
    # ------------------------------------------------------------------

    @BaseService.atomic
    def update_profile_picture(
        self,
        account_id: str,
        *,
        profile_picture: str,
    ) -> SocialAccountResult:
        """Update the profile picture URL for a social account."""
        account = self._get_or_raise(account_id)
        account.profile_picture = profile_picture
        account.save(update_fields=["profile_picture", "updated_at"])
        return SocialAccountResult.from_model(account)

    # ------------------------------------------------------------------
    # Update display name
    # ------------------------------------------------------------------

    @BaseService.atomic
    def update_display_name(
        self,
        account_id: str,
        *,
        display_name: str,
    ) -> SocialAccountResult:
        """Update the display name stored from the provider."""
        account = self._get_or_raise(account_id)
        account.display_name = display_name
        account.save(update_fields=["display_name", "updated_at"])
        return SocialAccountResult.from_model(account)

    # ------------------------------------------------------------------
    # Update last login
    # ------------------------------------------------------------------

    @BaseService.atomic
    def update_last_login(
        self,
        account_id: str,
        *,
        last_login_at: datetime.datetime | None = None,
    ) -> SocialAccountResult:
        """Record a login timestamp for the social account.

        Defaults to ``timezone.now()`` when *last_login_at* is ``None``.
        """
        account = self._get_or_raise(account_id)
        account.last_login_at = last_login_at or timezone.now()
        account.save(update_fields=["last_login_at", "updated_at"])
        return SocialAccountResult.from_model(account)

    # ------------------------------------------------------------------
    # Delete (hard-delete) social account
    # ------------------------------------------------------------------

    @BaseService.atomic
    def delete_account(self, account_id: str) -> None:
        """Permanently remove a social account record."""
        account = self._get_or_raise(account_id)
        account.delete()

    # ------------------------------------------------------------------
    # Disconnect provider (remove link for a user)
    # ------------------------------------------------------------------

    @BaseService.atomic
    def disconnect_provider(
        self,
        user,
        *,
        provider: str,
    ) -> None:
        """Remove the link between a user and a given social provider.

        Raises ``SocialAuthError`` if the user has no such link.
        """
        self._validate_provider(provider)
        account = SocialAccount.for_user_by_provider(user, provider)
        if not account:
            raise SocialAuthError(
                f"No {provider} account is linked to this user.",
            )
        account.delete()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_or_raise(account_id: str) -> SocialAccount:
        account = SocialAccount.objects.filter(pk=account_id).first()
        if not account:
            raise SocialAuthError(
                f"Social account '{account_id}' not found.",
            )
        return account

    @staticmethod
    def _validate_provider(provider: str) -> None:
        from apps.social_auth.constants import PROVIDER_REGISTRY

        if provider not in PROVIDER_REGISTRY:
            raise ProviderNotSupportedError(provider)

    @staticmethod
    def _raise_if_claimed_by_other(
        provider: str,
        provider_user_id: str,
        *,
        exclude_user=None,
    ) -> None:
        """Raise if the social identity is already linked to a different user."""
        qs = SocialAccount.objects.filter(
            provider=provider,
            provider_user_id=provider_user_id,
        )
        if exclude_user is not None:
            ct = ContentType.objects.get_for_model(exclude_user)
            qs = qs.exclude(content_type=ct, object_id=exclude_user.pk)

        if qs.exists():
            raise AccountAlreadyLinkedError(provider, provider_user_id)

    @staticmethod
    def _raise_if_already_linked(user, provider: str) -> None:
        """Raise if this user already has an account for this provider."""
        if SocialAccount.exists_for_user_and_provider(user, provider):
            raise SocialAuthError(
                f"You have already linked a {provider} account.",
            )
