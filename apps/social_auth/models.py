"""Social account model — stores provider-agnostic OAuth account links.

Links a local user (any domain: AdminUser, ITUser, ProfessorUser, CollegeUser,
FacultyUser) to an external social provider account via a polymorphic
GenericForeignKey. This avoids the limitation of ``AUTH_USER_MODEL`` which
can only point to a single model (AdminUser).
"""

from __future__ import annotations

import datetime
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Domain choices — must match AbstractDomainUser subclasses
# ---------------------------------------------------------------------------

USER_DOMAIN_CHOICES = [
    ("admin", _("Admin")),
    ("it", _("IT")),
    ("professor", _("Professor")),
    ("college", _("College")),
    ("faculty", _("Faculty")),
]

DOMAIN_USER_MODEL_MAP = {
    "admin": "accounts.AdminUser",
    "it": "accounts.ITUser",
    "professor": "accounts.ProfessorUser",
    "college": "accounts.CollegeUser",
    "faculty": "accounts.FacultyUser",
}


def resolve_user_model(domain: str) -> type:
    """Return the user model class for a given domain string."""
    from django.apps import apps

    label = DOMAIN_USER_MODEL_MAP.get(domain)
    if not label:
        raise ValueError(f"Unknown user domain: {domain}")
    return apps.get_model(label)


class SocialAccount(models.Model):
    """
    Links a local user to an external social provider account.

    Uses a polymorphic ``GenericForeignKey`` so a single ``SocialAccount``
    can reference any user model (AdminUser, ITUser, ProfessorUser, etc.).

    The ``user_domain`` field is denormalized for fast filtering without
    joining through ``ContentType``.
    """

    class ProviderChoices(models.TextChoices):
        """Supported OAuth identity providers."""

        GOOGLE = "google", _("Google")
        LINKEDIN = "linkedin", _("LinkedIn")
        MICROSOFT = "microsoft", _("Microsoft")
        GITHUB = "github", _("GitHub")

    # ------------------------------------------------------------------
    # Identification & Polymorphic User Relationship
    # ------------------------------------------------------------------
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
        help_text=_("Unique identifier for this social account link."),
    )

    # ContentType + object_id = polymorphic FK to ANY user model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("User Type"),
        help_text=_("The model class of the linked local user (AdminUser, ITUser, etc.)."),
    )
    object_id = models.UUIDField(
        db_index=True,
        verbose_name=_("User ID"),
        help_text=_("UUID of the linked local user."),
    )
    user = GenericForeignKey("content_type", "object_id")

    # Denormalized domain for fast filtering without a ContentType join
    user_domain = models.CharField(
        max_length=20,
        choices=USER_DOMAIN_CHOICES,
        db_index=True,
        verbose_name=_("User Domain"),
        help_text=_("Domain of the linked user (admin, it, professor, college, faculty)."),
    )

    # ------------------------------------------------------------------
    # Provider Details
    # ------------------------------------------------------------------
    provider = models.CharField(
        max_length=20,
        choices=ProviderChoices.choices,
        db_index=True,
        verbose_name=_("Provider"),
        help_text=_("OAuth identity provider name."),
    )
    provider_user_id = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_("Provider User ID"),
        help_text=_("Unique user ID assigned by the external provider."),
    )

    # ------------------------------------------------------------------
    # Profile Data (from provider)
    # ------------------------------------------------------------------
    email = models.EmailField(
        blank=True,
        default="",
        verbose_name=_("Email"),
        help_text=_("Email address returned by the provider (may differ from the local user email)."),
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Display Name"),
        help_text=_("Full display name from the provider."),
    )
    profile_picture = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name=_("Profile Picture"),
        help_text=_("URL of the profile picture from the provider."),
    )

    # ------------------------------------------------------------------
    # OAuth Tokens
    # ------------------------------------------------------------------
    access_token = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Access Token"),
        help_text=_(
            "OAuth access token used to call provider APIs on behalf of the user. "
            "Should be encrypted at rest in production."
        ),
    )
    refresh_token = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Refresh Token"),
        help_text=_(
            "OAuth refresh token used to obtain new access tokens after expiry. "
            "Should be encrypted at rest in production."
        ),
    )
    token_expiry = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Token Expiry"),
        help_text=_("Timestamp when the current access token expires."),
    )

    # ------------------------------------------------------------------
    # Verification & Activity
    # ------------------------------------------------------------------
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Verified Email"),
        help_text=_("Whether the provider has verified this email address."),
    )
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Login"),
        help_text=_("Timestamp of the most recent successful login via this provider."),
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when this social account link was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when this record was last updated."),
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        verbose_name = _("Social Account")
        verbose_name_plural = _("Social Accounts")
        db_table = "social_auth_account"
        constraints = [
            # Prevent the same social identity from being linked to multiple local users.
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"],
                name="uq_social_auth_provider_identity",
                violation_error_message=_(
                    "This social account is already linked to another user."
                ),
            ),
            # Prevent the same local user from linking the same provider twice.
            models.UniqueConstraint(
                fields=["provider", "content_type", "object_id"],
                name="uq_social_auth_provider_user",
                violation_error_message=_(
                    "You have already linked this provider."
                ),
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "content_type", "object_id"],
                name="idx_social_auth_provider_user",
            ),
            models.Index(
                fields=["email"],
                name="idx_social_auth_email",
            ),
            models.Index(
                fields=["last_login_at"],
                name="idx_social_auth_last_login",
            ),
        ]
        ordering = ["-created_at"]

    # ------------------------------------------------------------------
    # Query helpers (replaces ``filter(user=user)`` pattern)
    # ------------------------------------------------------------------

    @classmethod
    def filter_by_user(cls, user):
        """Return all ``SocialAccount`` records linked to the given user."""
        return cls.objects.filter(
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
        )

    @classmethod
    def filter_by_user_and_provider(cls, user, provider: str):
        """Return all ``SocialAccount`` records for a user + provider."""
        return cls.filter_by_user(user).filter(provider=provider)

    @classmethod
    def exists_for_user_and_provider(cls, user, provider: str) -> bool:
        """Check if a user has a specific provider linked."""
        return cls.filter_by_user_and_provider(user, provider).exists()

    @classmethod
    def for_user_by_provider(cls, user, provider: str):
        """Return a single ``SocialAccount`` for a user + provider or ``None``."""
        return cls.filter_by_user_and_provider(user, provider).first()

    @classmethod
    def resolve_user(cls, *, provider: str, provider_user_id: str):
        """Resolve the linked local user for a given provider identity.

        Returns the user model instance (AdminUser, ITUser, etc.) or
        ``None`` if no link exists.
        """
        account = (
            cls.objects.filter(
                provider=provider,
                provider_user_id=provider_user_id,
            )
            .select_related("content_type")
            .first()
        )
        return account.user if account else None

    # ------------------------------------------------------------------
    # Save helpers
    # ------------------------------------------------------------------

    @classmethod
    def create_for_user(
        cls,
        user,
        *,
        provider: str,
        provider_user_id: str,
        email: str = "",
        display_name: str = "",
        profile_picture: str = "",
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: datetime.datetime | None = None,
        is_verified: bool = False,
        last_login_at: datetime.datetime | None = None,
    ):
        """Create a ``SocialAccount`` linked to the given user (any domain).

        This is the single place where a ``SocialAccount`` is created,
        ensuring the content_type / user_domain fields are always set
        correctly from the user instance.
        """
        return cls.objects.create(
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
            user_domain=user.domain,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            display_name=display_name,
            profile_picture=profile_picture,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            is_verified=is_verified,
            last_login_at=last_login_at,
        )

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.get_provider_display()} — {self.email or self.provider_user_id}"

    def update_tokens(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: datetime.datetime | None = None,
    ) -> None:
        """Convenience method to update OAuth tokens on successful refresh."""
        if access_token is not None:
            self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token
        if token_expiry is not None:
            self.token_expiry = token_expiry
        self.save(
            update_fields=["access_token", "refresh_token", "token_expiry", "updated_at"]
        )

    def is_token_valid(self) -> bool:
        """Return True if the access token has not yet expired."""
        if self.token_expiry is None:
            return False
        return self.token_expiry > timezone.now()
