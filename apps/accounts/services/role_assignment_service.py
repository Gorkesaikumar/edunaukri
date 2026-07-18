from django.db import transaction

from apps.accounts.constants.enums import AccountStatus, ITUserRoleType
from apps.accounts.repositories.it_user_role_repository import ITUserRoleRepository
from apps.core.services.base import BaseService


class RoleAssignmentService(BaseService):
    def __init__(self, repository=None):
        self.repository = repository or ITUserRoleRepository()

    @transaction.atomic
    def assign_it_role(self, *, user, role: str, granted_by_id=None) -> None:
        valid = {choice.value for choice in ITUserRoleType}
        if role not in valid:
            raise ValueError("Invalid IT role.")
        self.repository.assign_role(
            user=user, role=role, is_primary=True, granted_by_id=granted_by_id
        )

    def get_it_roles(self, user) -> list[str]:
        return self.repository.get_roles(user)

    def user_has_it_role(self, user, role: str) -> bool:
        return self.repository.has_role(user, role)
