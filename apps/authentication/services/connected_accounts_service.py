"""Connected OAuth providers for job seeker accounts."""

from __future__ import annotations

from urllib.parse import quote

from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import ConnectedOAuthAccount, OAuthProvider
from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService


class ConnectedAccountsService(BaseService):
    PROVIDERS = (OAuthProvider.GOOGLE, OAuthProvider.LINKEDIN)

    def list_for_user(
        self,
        *,
        domain: str,
        user_id,
        settings_return_url: str | None = None,
        oauth_role: str | None = None,
    ) -> list[dict]:
        settings_path = settings_return_url or self._default_settings_return_path(
            domain=domain, user_id=user_id
        )
        existing = {
            row.provider: row
            for row in ConnectedOAuthAccount.objects.filter(
                domain=domain, user_id=user_id, is_deleted=False
            )
        }
        role_param = oauth_role or self._oauth_role_for_domain(domain)
        items = []
        for provider in self.PROVIDERS:
            row = existing.get(provider)
            connected = bool(row and row.is_connected)
            connect_url = (
                reverse(f"oauth_{provider}")
                + f"?intent=connect&role={role_param}&return={quote(settings_path, safe='')}"
            )
            items.append(
                {
                    "provider": provider,
                    "label": OAuthProvider(provider).label,
                    "connected": connected,
                    "provider_email": row.provider_email if connected and row else "",
                    "connected_label": timezone.localtime(row.connected_at).strftime(
                        "%b %d, %Y"
                    )
                    if connected and row and row.connected_at
                    else "",
                    "connect_url": connect_url,
                    "configured": self._provider_configured(provider),
                }
            )
        return items

    @staticmethod
    def _default_settings_return_path(*, domain: str, user_id) -> str:
        if domain == "professor":
            return reverse("professor_portal_entry")
        if domain == "college":
            return reverse("college_portal_entry")
        if domain == DomainType.IT:
            from apps.accounts.constants.enums import ITUserRoleType
            from apps.accounts.models.it_user import ITUser
            from apps.accounts.services.role_assignment_service import (
                RoleAssignmentService,
            )

            user = ITUser.objects.filter(pk=user_id, is_deleted=False).first()
            if user is not None and RoleAssignmentService().user_has_it_role(
                user, ITUserRoleType.RECRUITER
            ):
                return reverse("recruiter_portal_entry")
        return reverse("jobseeker_portal_entry")

    @staticmethod
    def _oauth_role_for_domain(domain: str) -> str:
        if domain == "professor":
            return "professor"
        if domain == "college":
            return "college"
        return "seeker"

    @staticmethod
    def _provider_configured(provider: str) -> bool:
        from apps.authentication.constants.oauth_config import provider_configured

        return provider_configured(provider)

    @BaseService.atomic
    def disconnect(
        self, *, domain: str, user_id, provider: str, request_meta: dict | None = None
    ) -> dict:
        if provider not in OAuthProvider.values:
            raise ValidationException("Unknown provider.")
        row = ConnectedOAuthAccount.objects.filter(
            domain=domain, user_id=user_id, provider=provider, is_deleted=False
        ).first()
        if not row or not row.is_connected:
            raise ValidationException("This account is not connected.")
        row.disconnected_at = timezone.now()
        row.save(update_fields=["disconnected_at", "updated_at"])
        AuthAuditService().record_oauth_disconnected(
            domain=domain,
            user_id=user_id,
            provider=provider,
            request_meta=request_meta,
        )
        return {"provider": provider, "connected": False}
