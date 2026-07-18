"""Resolve, link, and create college users from OAuth identity profiles."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.college_user import CollegeUser
from apps.authentication.models import ConnectedOAuthAccount
from apps.authentication.services.oauth_account_service import OAuthIdentity
from apps.core.services.base import BaseService

COLLEGE_OAUTH_DOMAIN = "college"


class CollegeOAuthAccountService(BaseService):
    @BaseService.atomic
    def resolve_or_create_college_user(self, identity: OAuthIdentity) -> CollegeUser:
        linked = self._find_by_provider(identity)
        if linked:
            user = CollegeUser.objects.filter(
                pk=linked.user_id, is_deleted=False, is_active=True
            ).first()
            if not user:
                raise ValidationError("Linked account is no longer active.")
            self._upsert_connection(user, identity)
            return user

        user = CollegeUser.objects.filter(
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

        user = CollegeUser.objects.create(
            email=identity.email.lower(),
            account_status=AccountStatus.ACTIVE
            if identity.email_verified
            else AccountStatus.PENDING_VERIFICATION,
            email_verified=identity.email_verified,
        )
        user.set_unusable_password()
        user.save(update_fields=["password", "updated_at"])
        self._upsert_connection(user, identity)
        return user

    @BaseService.atomic
    def link_provider_to_user(
        self, user: CollegeUser, identity: OAuthIdentity
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
            domain=COLLEGE_OAUTH_DOMAIN,
            provider=identity.provider,
            provider_user_id=identity.provider_user_id,
            is_deleted=False,
            disconnected_at__isnull=True,
        ).first()

    def _upsert_connection(
        self, user: CollegeUser, identity: OAuthIdentity
    ) -> ConnectedOAuthAccount:
        row = ConnectedOAuthAccount.objects.filter(
            domain=COLLEGE_OAUTH_DOMAIN,
            user_id=user.pk,
            provider=identity.provider,
            is_deleted=False,
        ).first()
        was_connected = bool(row and row.is_connected)
        if not row:
            row = ConnectedOAuthAccount.objects.create(
                domain=COLLEGE_OAUTH_DOMAIN,
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
                domain=COLLEGE_OAUTH_DOMAIN,
                user_id=user.pk,
                provider=identity.provider,
            )
        return row
