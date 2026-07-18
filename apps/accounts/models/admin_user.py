from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.accounts.models.base import AbstractDomainUser


class AdminUser(AbstractDomainUser, PermissionsMixin):
    """Platform administrator — Django AUTH_USER_MODEL."""

    is_staff = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"
        db_table = "accounts_admin_user"

    @property
    def domain(self):
        return "admin"
