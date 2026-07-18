"""Resolve, link, and create professor users from OAuth identity profiles."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.academic_recruitment.models import ProfessorProfile
from apps.authentication.models import ConnectedOAuthAccount, OAuthProvider
from apps.authentication.services.oauth_account_service import OAuthIdentity
from apps.core.services.base import BaseService
from apps.it_recruitment.services.web_registration_service import split_full_name

PROFESSOR_OAUTH_DOMAIN = "professor"


class ProfessorOAuthAccountService(BaseService):
    @BaseService.atomic
    def resolve_or_create_professor_user(
        self, identity: OAuthIdentity
    ) -> ProfessorUser:
        linked = self._find_by_provider(identity)
        if linked:
            user = ProfessorUser.objects.filter(
                pk=linked.user_id, is_deleted=False, is_active=True
            ).first()
            if not user:
                raise ValidationError("Linked account is no longer active.")
            self._upsert_connection(user, identity)
            return user

        user = ProfessorUser.objects.filter(
            email=identity.email.lower(), is_deleted=False
        ).first()
        if user:
            self._upsert_connection(user, identity)
            if identity.email_verified and not user.email_verified:
                user.email_verified = True
                if user.account_status == AccountStatus.PENDING_VERIFICATION:
                    user.account_status = AccountStatus.ACTIVE
                user.save(
                    update_fields=["email_verified", "account_status", "updated_at"]
                )
            return user

        user = ProfessorUser.objects.create(
            email=identity.email.lower(),
            account_status=AccountStatus.ACTIVE
            if identity.email_verified
            else AccountStatus.PENDING_VERIFICATION,
            email_verified=identity.email_verified,
        )
        user.set_unusable_password()
        user.save()
        self._create_minimal_profile(user, identity=identity)
        self._upsert_connection(user, identity)
        return user

    @BaseService.atomic
    def link_provider_to_user(
        self, user: ProfessorUser, identity: OAuthIdentity
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
            domain=PROFESSOR_OAUTH_DOMAIN,
            provider=identity.provider,
            provider_user_id=identity.provider_user_id,
            is_deleted=False,
            disconnected_at__isnull=True,
        ).first()

    def _upsert_connection(
        self, user: ProfessorUser, identity: OAuthIdentity
    ) -> ConnectedOAuthAccount:
        row = ConnectedOAuthAccount.objects.filter(
            domain=PROFESSOR_OAUTH_DOMAIN,
            user_id=user.pk,
            provider=identity.provider,
            is_deleted=False,
        ).first()
        was_connected = bool(row and row.is_connected)
        if not row:
            row = ConnectedOAuthAccount.objects.create(
                domain=PROFESSOR_OAUTH_DOMAIN,
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
                domain=PROFESSOR_OAUTH_DOMAIN,
                user_id=user.pk,
                provider=identity.provider,
            )
        return row

    def _create_minimal_profile(
        self, user: ProfessorUser, *, identity: OAuthIdentity
    ) -> None:
        if ProfessorProfile.objects.filter(user=user).exists():
            return
        first = identity.first_name
        last = identity.last_name
        if not first and not last:
            first, last = split_full_name(identity.email.split("@")[0])
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.PROFESSOR,
            data={"first_name": first, "last_name": last},
        )
