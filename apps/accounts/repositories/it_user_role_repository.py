from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.it_user_role import ITUserRole
from apps.core.repositories.base import BaseRepository


class ITUserRoleRepository(BaseRepository):
    model = ITUserRole

    def assign_role(
        self, *, user, role: str, is_primary: bool = True, granted_by_id=None
    ) -> ITUserRole:
        obj, _ = ITUserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={"is_primary": is_primary, "granted_by_id": granted_by_id},
        )
        return obj

    def get_roles(self, user) -> list[str]:
        return list(user.roles.filter(is_deleted=False).values_list("role", flat=True))

    def has_role(self, user, role: str) -> bool:
        return user.roles.filter(role=role, is_deleted=False).exists()

    def primary_role(self, user) -> str | None:
        primary = user.roles.filter(is_primary=True, is_deleted=False).first()
        return primary.role if primary else None
