from django.db import models

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.it_user import ITUser
from apps.core.models.base import BaseModel


class ITUserRole(BaseModel):
    """Role assignment for IT domain users."""

    user = models.ForeignKey(ITUser, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(
        max_length=20, choices=ITUserRoleType.choices, db_index=True
    )
    is_primary = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "accounts_it_user_role"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"], name="unique_it_user_role"
            ),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.role}"
