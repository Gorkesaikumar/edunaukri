from django.db import models

from apps.accounts.models.base import AbstractDomainUser


class ProfessorUser(AbstractDomainUser):
    """Engineering Faculty domain — professor identity."""

    email_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Professor User"
        verbose_name_plural = "Professor Users"
        db_table = "accounts_professor_user"

    @property
    def domain(self):
        return "professor"
