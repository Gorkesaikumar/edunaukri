"""Validate URL-scoped user UUID against authenticated JWT/session identity."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from apps.authentication.services.auth_audit_service import AuthAuditService
from apps.authentication.services.identity_service import IdentityService
from apps.authentication.utils.user_agent import parse_user_agent
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService


class RouteAuthorizationService(BaseService):
    """Ensure authenticated users only access their own UUID-scoped portal routes."""

    def assert_url_user_matches(
        self,
        *,
        request,
        authenticated_user,
        url_user_uuid,
        portal: str,
    ) -> None:
        if IdentityService.uuids_match(authenticated_user.pk, url_user_uuid):
            return
        self.record_unauthorized_access(
            authenticated_user=authenticated_user,
            requested_uuid=url_user_uuid,
            request=request,
            portal=portal,
        )
        raise PermissionDenied("You may not access another user's portal.")

    def record_unauthorized_access(
        self,
        *,
        authenticated_user,
        requested_uuid,
        request,
        portal: str,
    ) -> None:
        meta = self._request_meta(request)
        ua = parse_user_agent(meta.get("user_agent", ""))
        from apps.accounts.models.professor_user import ProfessorUser
        from apps.accounts.models.college_user import CollegeUser
        domain = DomainType.FACULTY if isinstance(authenticated_user, (ProfessorUser, CollegeUser)) else DomainType.IT
        AuthAuditService().record_unauthorized_uuid_access(
            domain=domain,
            user_id=authenticated_user.pk,
            authenticated_uuid=str(authenticated_user.pk),
            requested_uuid=str(requested_uuid),
            requested_path=request.path,
            portal=portal,
            request_meta={
                **meta,
                "browser": ua["browser"],
                "os_name": ua["os_name"],
                "device_label": ua["device_label"],
            },
        )

    @staticmethod
    def _request_meta(request) -> dict:
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
