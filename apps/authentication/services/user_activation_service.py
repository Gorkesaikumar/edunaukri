from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.repositories.user_repository import get_user_repository
from apps.core.services.base import BaseService


class UserActivationService(BaseService):
    @transaction.atomic
    def activate(self, *, domain: str, user_id) -> None:
        user = self._get_user(domain, user_id)
        user.account_status = AccountStatus.ACTIVE
        user.is_active = True
        user.save(update_fields=["account_status", "is_active", "updated_at"])

    @transaction.atomic
    def suspend(self, *, domain: str, user_id) -> None:
        user = self._get_user(domain, user_id)
        user.account_status = AccountStatus.SUSPENDED
        user.is_active = False
        user.save(update_fields=["account_status", "is_active", "updated_at"])

    @transaction.atomic
    def deactivate(self, *, domain: str, user_id) -> None:
        user = self._get_user(domain, user_id)
        user.account_status = AccountStatus.DEACTIVATED
        user.is_active = False
        user.save(update_fields=["account_status", "is_active", "updated_at"])

    def _get_user(self, domain, user_id):
        user = get_user_repository(domain).get_by_id(user_id)
        if not user:
            raise ValidationError("User not found.")
        return user
