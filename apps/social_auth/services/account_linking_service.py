"""Google account linking — resolve or create local user from a verified Google profile.

Workflow
--------
1. Receive verified ``GoogleTokenData``.
2. Search existing ``SocialAccount`` by provider + provider_user_id.
   - **Found** → return the linked local user immediately.
3. Search existing user by verified email (domain-aware).
   - **Found** → create ``SocialAccount`` linking the user → return user.
4. Neither found → create new user + profile + ``SocialAccount`` (domain/role-aware).
5. Return the user with a flag indicating whether it was newly created.

All steps execute inside a single database transaction with row-level locks
to prevent race conditions.

Domain / Role Matrix
--------------------
+---------------+------------+------------------+----------------------+
| Domain        | Role       | User Model       | Profile Type         |
+---------------+------------+------------------+----------------------+
| it            | seeker     | ITUser           | JobSeekerProfile     |
| it            | recruiter  | ITUser           | RecruiterProfile     |
| professor     | seeker     | ProfessorUser    | ProfessorProfile     |
| college       | institution| CollegeUser      | College              |
+---------------+------------+------------------+----------------------+
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from apps.accounts.constants.enums import AccountStatus, ITUserRoleType
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.core.exceptions.domain_exceptions import DomainException
from apps.core.services.base import BaseService
from apps.it_recruitment.services.web_registration_service import split_full_name
from apps.social_auth.exceptions import CrossDomainLinkedError, SocialAuthError
from apps.social_auth.models import SocialAccount
from apps.social_auth.services.domain_role_service import DomainRoleService
from apps.social_auth.services.google_service import GoogleTokenData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strongly-typed result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountLinkingResult:
    """Result of resolving or creating a local user from a Google profile."""

    user: object = field(repr=False)
    """The user instance (existing or newly created) — could be any domain."""

    was_created: bool
    """``True`` when a brand-new user account was registered."""

    social_account_id: str
    """UUID of the ``SocialAccount`` record (created or pre-existing)."""


# ---------------------------------------------------------------------------
# Domain / role validation
# ---------------------------------------------------------------------------

VALID_DOMAIN_ROLES = frozenset({
    ("it", "seeker"),
    ("it", "recruiter"),
    ("professor", "seeker"),
    ("college", "institution"),
    ("admin", "admin"),
})

DEFAULT_DOMAIN = "it"
DEFAULT_ROLE = "seeker"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GoogleAccountLinkingService(BaseService):
    """Orchestrates the enterprise Google sign-in / account-linking workflow.

    This service resolves or creates a local user based on the verified
    Google profile AND the domain+role context from the initiating login
    page.
    """

    @BaseService.atomic
    def resolve_or_create(
        self,
        profile: GoogleTokenData,
        *,
        domain: str = DEFAULT_DOMAIN,
        role: str = DEFAULT_ROLE,
    ) -> AccountLinkingResult:
        """Resolve an existing local user or create a new one from a Google profile.

        **Workflow decision tree**

        ::

            GoogleTokenData
                │
                ├─ SocialAccount exists? ──► return linked user
                │
                ├─ User by email (domain)? ──► link account → return
                │
                └─ Create new user
                     ├─ domain="it", role="seeker"    → ITUser + JobSeekerProfile
                     ├─ domain="it", role="recruiter" → ITUser + RecruiterProfile
                     ├─ domain="professor", role="seeker" → ProfessorUser + ProfessorProfile
                     ├─ domain="college", role="institution" → CollegeUser (profile later)
                     └─ SocialAccount → return

        Args:
            profile: The verified Google token data.
            domain: User domain ("it", "professor", "college").
            role: User role within the domain ("seeker", "recruiter",
                "institution").

        Returns:
            ``AccountLinkingResult`` with the user, a creation flag, and
            the social account UUID.

        Raises:
            SocialAuthError: If the email is empty or the domain/role
                combination is not supported.
        """
        # ------------------------------------------------------------------
        # 1. Look up by social identity (domain-agnostic)
        # ------------------------------------------------------------------
        social_account = self._find_social_account(profile)
        if social_account is not None:
            linked_user = social_account.user
            if linked_user is not None:
                logger.info(
                    "Existing SocialAccount found for %s (user=%s, domain=%s)",
                    profile.email, linked_user.pk, domain,
                )
                # ---- Cross-domain/role detection ----
                DomainRoleService.validate_portal_match_from_social_account(
                    social_account,
                    linked_user,
                    requested_domain=domain,
                    requested_role=role,
                )
                # ---- End cross-domain detection ----
                return AccountLinkingResult(
                    user=linked_user,
                    was_created=False,
                    social_account_id=str(social_account.pk),
                )
            # Orphaned SocialAccount — referenced user no longer exists.
            # Delete the stale record and fall through to create a fresh user.
            logger.warning(
                "Orphaned SocialAccount %s (provider_user_id=%s) has no linked user. "
                "Deleting and re-creating.",
                social_account.pk, profile.google_user_id,
            )
            social_account.delete()

        # ------------------------------------------------------------------
        # 2. Look up by verified email (domain-aware)
        # ------------------------------------------------------------------
        user = self._find_existing_user(profile, domain=domain)
        if user is not None:
            logger.info(
                "Existing %s user found by email %s (pk=%s)",
                domain, profile.email, user.pk,
            )
            # User exists — just link the social account.  The role they
            # already have is preserved (we never overwrite roles).
            social_account = self._link_social_account(user, profile)
            return AccountLinkingResult(
                user=user,
                was_created=False,
                social_account_id=str(social_account.pk),
            )

        # ------------------------------------------------------------------
        # 2b. Cross-domain email lookup — user in another domain?
        # ------------------------------------------------------------------
        cross_domain_result = self._find_existing_user_cross_domain(profile)
        if cross_domain_result is not None:
            existing_user, existing_domain = cross_domain_result
            existing_role = DomainRoleService.resolve_user_role(existing_user, existing_domain)
            logger.info(
                "Cross-domain email match: %s found as %s/%s (pk=%s), "
                "requested domain=%s, role=%s",
                profile.email, existing_domain, existing_role,
                existing_user.pk, domain, role,
            )
            # Raise CrossDomainLinkedError via the domain-agnostic validator
            DomainRoleService.validate_portal_match(
                existing_user,
                linked_domain=existing_domain,
                linked_role=existing_role,
                linked_email=profile.email,
                requested_domain=domain,
                requested_role=role,
            )

        # ------------------------------------------------------------------
        # 3. Create new user (domain/role-aware)
        # ------------------------------------------------------------------
        logger.info(
            "Creating new %s user for %s (domain=%s, role=%s)",
            domain, profile.email, domain, role,
        )
        user, social_account = self._create_new_user(
            profile, domain=domain, role=role,
        )
        if user is None:
            raise SocialAuthError(
                f"Account creation failed for {profile.email}. "
                "User object was not created."
            )
        logger.info(
            "Successfully created %s user %s (pk=%s)",
            domain, profile.email, user.pk,
        )
        return AccountLinkingResult(
            user=user,
            was_created=True,
            social_account_id=str(social_account.pk),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_social_account(
        profile: GoogleTokenData,
    ) -> SocialAccount | None:
        """Look up an existing ``SocialAccount`` by provider identity."""
        return (
            SocialAccount.objects.select_for_update()
            .filter(
                provider=SocialAccount.ProviderChoices.GOOGLE,
                provider_user_id=profile.google_user_id,
            )
            .select_related("content_type")
            .first()
        )

    @staticmethod
    def _find_existing_user(profile: GoogleTokenData, *, domain: str):
        """Find a user whose verified email matches the Google profile."""
        email = profile.email.lower().strip()
        if not email or not profile.verified_email:
            return None

        user_model = _domain_user_model(domain)
        if user_model is None:
            return None

        return (
            user_model.objects.select_for_update()
            .filter(email=email, is_deleted=False, is_active=True)
            .first()
        )

    @staticmethod
    def _find_existing_user_cross_domain(
        profile: GoogleTokenData,
    ) -> tuple | None:
        """Search ALL domain user models for a matching verified email.

        This prevents duplicate account creation when a user already has
        an account in one domain (e.g. IT Job Seeker via email/password)
        and attempts to sign up via Google OAuth from another domain
        (e.g. Faculty Professor).

        Returns:
            A tuple ``(user, domain)`` for the first match found, or
            ``None`` if no user exists in any domain.
        """
        email = profile.email.lower().strip()
        if not email or not profile.verified_email:
            return None

        for domain_key in ("it", "professor", "college"):
            user_model = _domain_user_model(domain_key)
            if user_model is None:
                continue
            user = (
                user_model.objects.select_for_update()
                .filter(email=email, is_deleted=False, is_active=True)
                .first()
            )
            if user is not None:
                return (user, domain_key)

        return None

    @staticmethod
    def _link_social_account(user, profile: GoogleTokenData) -> SocialAccount:
        """Create a ``SocialAccount`` linking a pre-existing user to Google."""
        if SocialAccount.exists_for_user_and_provider(
            user, SocialAccount.ProviderChoices.GOOGLE,
        ):
            raise SocialAuthError(
                "This user already has a Google account linked."
            )

        return SocialAccount.create_for_user(
            user=user,
            provider=SocialAccount.ProviderChoices.GOOGLE,
            provider_user_id=profile.google_user_id,
            email=profile.email,
            display_name=profile.name,
            profile_picture=profile.picture,
            is_verified=profile.verified_email,
        )

    @staticmethod
    def _create_new_user(
        profile: GoogleTokenData,
        *,
        domain: str = DEFAULT_DOMAIN,
        role: str = DEFAULT_ROLE,
    ) -> tuple:
        """Create a user, role-appropriate profile, and ``SocialAccount``.

        The domain+role combination determines which user model and
        profile type are created.
        """
        email = profile.email.lower().strip()
        if not email:
            raise SocialAuthError(
                "Cannot create an account without an email address."
            )

        if (domain, role) not in VALID_DOMAIN_ROLES:
            raise SocialAuthError(
                f"Unsupported domain/role combination: '{domain}/{role}'."
            )

        creators = {
            ("it", "seeker"): _create_it_seeker,
            ("it", "recruiter"): _create_it_recruiter,
            ("professor", "seeker"): _create_professor,
            ("college", "institution"): _create_college_user,
        }

        creator = creators[(domain, role)]
        return creator(profile, email)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _domain_user_model(domain: str):
    """Return the user model class for a given domain."""
    from apps.social_auth.models import DOMAIN_USER_MODEL_MAP, resolve_user_model

    return resolve_user_model(domain) if domain in DOMAIN_USER_MODEL_MAP else None


def _split_name(profile: GoogleTokenData, email: str):
    """Split the Google display name into first/last, falling back to email local-part."""
    first_name, last_name = split_full_name(profile.name)
    if not first_name:
        first_name, last_name = split_full_name(email.split("@")[0])
    return first_name, last_name


def _create_common_social_account(
    user, profile: GoogleTokenData,
) -> SocialAccount:
    """Create the SocialAccount for any user type."""
    return SocialAccount.create_for_user(
        user=user,
        provider=SocialAccount.ProviderChoices.GOOGLE,
        provider_user_id=profile.google_user_id,
        email=profile.email,
        display_name=profile.name,
        profile_picture=profile.picture,
        is_verified=profile.verified_email,
    )


# ===================================================================
# IT Domain
# ===================================================================


def _create_it_seeker(
    profile: GoogleTokenData,
    email: str,
) -> tuple:
    """Create ITUser + JobSeekerProfile + SocialAccount."""
    user = ITUser.objects.create(
        email=email,
        account_status=(
            AccountStatus.ACTIVE if profile.verified_email
            else AccountStatus.PENDING_VERIFICATION
        ),
        email_verified=profile.verified_email,
    )
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])

    RoleAssignmentService().assign_it_role(
        user=user, role=ITUserRoleType.JOB_SEEKER
    )

    first_name, last_name = _split_name(profile, email)
    try:
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.JOB_SEEKER,
            data={"first_name": first_name, "last_name": last_name},
        )
    except DomainException as exc:
        logger.warning(
            "Job seeker profile creation failed (recoverable): %s", exc,
        )
    except Exception as exc:
        logger.warning(
            "Job seeker profile creation failed unexpectedly (recoverable): %s",
            exc,
        )

    social_account = _create_common_social_account(user, profile)
    return user, social_account


def _create_it_recruiter(
    profile: GoogleTokenData,
    email: str,
) -> tuple:
    """Create ITUser + RecruiterProfile + SocialAccount."""
    user = ITUser.objects.create(
        email=email,
        account_status=(
            AccountStatus.ACTIVE if profile.verified_email
            else AccountStatus.PENDING_VERIFICATION
        ),
        email_verified=profile.verified_email,
    )
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])

    RoleAssignmentService().assign_it_role(
        user=user, role=ITUserRoleType.RECRUITER
    )

    first_name, last_name = _split_name(profile, email)
    try:
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.RECRUITER,
            data={"first_name": first_name, "last_name": last_name},
        )
    except DomainException as exc:
        logger.warning(
            "Recruiter profile creation failed (recoverable): %s", exc,
        )
    except Exception as exc:
        logger.warning(
            "Recruiter profile creation failed unexpectedly (recoverable): %s",
            exc,
        )

    social_account = _create_common_social_account(user, profile)
    return user, social_account


# ===================================================================
# Faculty Domain — Job Seeker (Professor)
# ===================================================================


def _create_professor(
    profile: GoogleTokenData,
    email: str,
) -> tuple:
    """Create ProfessorUser + ProfessorProfile + SocialAccount."""
    user = ProfessorUser.objects.create(
        email=email,
        account_status=(
            AccountStatus.ACTIVE if profile.verified_email
            else AccountStatus.PENDING_VERIFICATION
        ),
        email_verified=profile.verified_email,
    )
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])

    first_name, last_name = _split_name(profile, email)
    try:
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.PROFESSOR,
            data={"first_name": first_name, "last_name": last_name},
        )
    except DomainException as exc:
        # Domain-specific errors (ConflictException, ValidationException, etc.)
        # are recoverable — the user account is created; they can complete
        # their profile later via the settings page.
        logger.warning(
            "Professor profile creation failed (recoverable): %s", exc,
        )
    except Exception as exc:
        # Non-domain errors (IntegrityError, etc.) — also recoverable.
        # The user account exists; they can complete their profile later.
        logger.warning(
            "Professor profile creation failed unexpectedly (recoverable): %s",
            exc,
        )

    social_account = _create_common_social_account(user, profile)
    return user, social_account


# ===================================================================
# Faculty Domain — Institution (College)
# ===================================================================


def _create_college_user(
    profile: GoogleTokenData,
    email: str,
) -> tuple:
    """Create CollegeUser + SocialAccount (college profile is completed later).

    Unlike IT or professor profiles, creating a College requires extensive
    institution-specific data (name, type, accreditation, etc.) that is
    not available from the Google profile.  The user account is created
    and they complete their institution profile via the settings page.
    """
    user = CollegeUser.objects.create(
        email=email,
        account_status=(
            AccountStatus.ACTIVE if profile.verified_email
            else AccountStatus.PENDING_VERIFICATION
        ),
        email_verified=profile.verified_email,
    )
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])

    # Create a minimal profile — the institution can fill in details later
    first_name, last_name = _split_name(profile, email)
    try:
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.COLLEGE,
            data={
                "first_name": first_name,
                "last_name": last_name,
                "name": profile.name or "My Institution",
            },
        )
    except DomainException as exc:
        # College creation requires more data; if it fails, we still
        # create the user so they can complete setup later.
        logger.warning(
            "College profile creation failed (recoverable): %s", exc,
        )
    except Exception as exc:
        # College creation requires more data; if it fails, we still
        # create the user so they can complete setup later.
        logger.warning(
            "College profile creation failed unexpectedly (recoverable): %s",
            exc,
        )

    social_account = _create_common_social_account(user, profile)
    return user, social_account
