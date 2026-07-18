from django.db import models

from apps.accounts.models.base import AbstractDomainUser


class ITUser(AbstractDomainUser):
    """IT Recruitment domain user (job seekers, recruiters)."""

    email_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "IT User"
        verbose_name_plural = "IT Users"
        db_table = "accounts_it_user"

    @property
    def domain(self):
        return "it"
