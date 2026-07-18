from django.utils import timezone

from apps.authentication.models import AuthToken
from apps.core.repositories.crud import CRUDRepository


class AuthTokenRepository(CRUDRepository):
    model = AuthToken

    def invalidate_pending(self, *, domain: str, user_id, purpose: str) -> None:
        self.filter_by(
            domain=domain, user_id=user_id, purpose=purpose, used_at__isnull=True
        ).update(is_deleted=True, deleted_at=timezone.now())

    def get_by_hash(self, *, domain: str, token_hash: str, purpose: str):
        return self.filter_by(
            domain=domain, token_hash=token_hash, purpose=purpose
        ).first()
