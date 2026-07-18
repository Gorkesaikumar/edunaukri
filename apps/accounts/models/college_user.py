from django.db import models

from apps.accounts.models.base import AbstractDomainUser


class CollegeUser(AbstractDomainUser):
    """Engineering Faculty domain — college representative identity."""

    email_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "College User"
        verbose_name_plural = "College Users"
        db_table = "accounts_college_user"

    @property
    def domain(self):
        return "college"
