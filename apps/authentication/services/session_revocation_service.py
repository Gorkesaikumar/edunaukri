from django.utils import timezone

from apps.authentication.models.session_revocation import SessionRevocation
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.core.services.base import BaseService


class SessionRevocationService(BaseService):
    @BaseService.atomic
    def revoke_sessions(
        self, *, domain: str, user_id, admin_id=None
    ) -> SessionRevocation:
        SessionManagementService().force_revoke_all_for_user(
            domain=domain, user_id=user_id
        )
        revocation, _ = SessionRevocation.objects.update_or_create(
            domain=domain,
            user_id=user_id,
            defaults={"revoked_at": timezone.now(), "revoked_by_id": admin_id},
        )
        return revocation

    def get_revoked_at(self, *, domain: str, user_id):
        row = SessionRevocation.objects.filter(domain=domain, user_id=user_id).first()
        return row.revoked_at if row else None
