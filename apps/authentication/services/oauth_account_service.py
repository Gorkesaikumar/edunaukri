"""Resolve, link, and create IT users from OAuth identity profiles."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus, ITUserRoleType
from apps.accounts.models.it_user import ITUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.models import ConnectedOAuthAccount, OAuthProvider
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.it_recruitment.services.web_registration_service import split_full_name


@dataclass(frozen=True)
class OAuthIdentity:
    provider: str
    provider_user_id: str
    email: str
    first_name: str
    last_name: str
    email_verified: bool = True


class OAuthAccountService(BaseService):
    """Link OAuth identities to permanent IT user UUIDs."""

    ROLE_MAP = {
        "seeker": ITUserRoleType.JOB_SEEKER,
        "recruiter": ITUserRoleType.RECRUITER,
    }

    @BaseService.atomic
    def resolve_or_create_it_user(
        self, identity: OAuthIdentity, *, intended_role: str
    ) -> ITUser:
        role = self.ROLE_MAP.get(intended_role)
        if not role:
            raise ValidationError("Invalid account type for sign-in.")

        linked = self._find_by_provider(identity)
        if linked:
            user = ITUser.objects.filter(
                pk=linked.user_id, is_deleted=False, is_active=True
            ).first()
            if not user:
                raise ValidationError("Linked account is no longer active.")
            self._ensure_role(user, role)
            self._upsert_connection(user, identity)
            return user

        user = ITUser.objects.filter(
            email=identity.email.lower(), is_deleted=False
        ).first()
        if user:
            self._ensure_role(user, role)
            self._upsert_connection(user, identity)
            if identity.email_verified and not user.email_verified:
                user.email_verified = True
                if user.account_status == AccountStatus.PENDING_VERIFICATION:
                    user.account_status = AccountStatus.ACTIVE
                user.save(
                    update_fields=["email_verified", "account_status", "updated_at"]
                )
            return user

        user = ITUser.objects.create(
            email=identity.email.lower(),
            account_status=AccountStatus.ACTIVE
            if identity.email_verified
            else AccountStatus.PENDING_VERIFICATION,
            email_verified=identity.email_verified,
        )
        user.set_unusable_password()
        user.save()
        RoleAssignmentService().assign_it_role(user=user, role=role)
        self._create_minimal_profile(user, role=role, identity=identity)
        self._upsert_connection(user, identity)
        return user

    @BaseService.atomic
    def link_provider_to_user(
        self, user: ITUser, identity: OAuthIdentity
    ) -> ConnectedOAuthAccount:
        if user.email.lower() != identity.email.lower():
            raise ValidationError(
                "The email on your social account does not match your EduNaukri account email."
            )
        linked = self._find_by_provider(identity)
        if linked and linked.user_id != user.pk:
            raise ValidationError(
                "This social account is already linked to another EduNaukri user."
            )
        return self._upsert_connection(user, identity)

    def _find_by_provider(
        self, identity: OAuthIdentity
    ) -> ConnectedOAuthAccount | None:
        return ConnectedOAuthAccount.objects.filter(
            domain=DomainType.IT,
            provider=identity.provider,
            provider_user_id=identity.provider_user_id,
            is_deleted=False,
            disconnected_at__isnull=True,
        ).first()

    def _ensure_role(self, user: ITUser, role: str) -> None:
        roles = RoleAssignmentService()
        if not roles.user_has_it_role(user, role):
            label = "Job Seeker" if role == ITUserRoleType.JOB_SEEKER else "Recruiter"
            raise ValidationError(
                f"This account is not registered as a {label}. Switch to the correct account type and try again."
            )

    def _upsert_connection(
        self, user: ITUser, identity: OAuthIdentity
    ) -> ConnectedOAuthAccount:
        row = ConnectedOAuthAccount.objects.filter(
            domain=DomainType.IT,
            user_id=user.pk,
            provider=identity.provider,
            is_deleted=False,
        ).first()
        was_connected = bool(row and row.is_connected)
        if not row:
            row = ConnectedOAuthAccount.objects.create(
                domain=DomainType.IT,
                user_id=user.pk,
                provider=identity.provider,
                created_by_id=user.pk,
            )
        row.provider_user_id = identity.provider_user_id
        row.provider_email = identity.email
        row.connected_at = timezone.now()
        row.disconnected_at = None
        row.is_deleted = False
        row.save(
            update_fields=[
                "provider_user_id",
                "provider_email",
                "connected_at",
                "disconnected_at",
                "is_deleted",
                "updated_at",
            ]
        )
        if not was_connected:
            from apps.authentication.services.auth_audit_service import AuthAuditService

            AuthAuditService().record_oauth_connected(
                domain=DomainType.IT,
                user_id=user.pk,
                provider=identity.provider,
            )
        return row

    def _create_minimal_profile(
        self, user: ITUser, *, role: str, identity: OAuthIdentity
    ) -> None:
        first = identity.first_name
        last = identity.last_name
        if not first and not last:
            first, last = split_full_name(identity.email.split("@")[0])

        if role == ITUserRoleType.JOB_SEEKER:
            if JobSeekerProfile.objects.filter(user=user).exists():
                return
            ProfileService().create_profile(
                user=user,
                profile_type=ProfileType.JOB_SEEKER,
                data={"first_name": first, "last_name": last},
            )
            return

        if RecruiterProfile.objects.filter(user=user).exists():
            return
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.RECRUITER,
            data={"first_name": first, "last_name": last},
        )
