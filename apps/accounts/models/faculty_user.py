from django.db import models

from apps.accounts.models.base import AbstractDomainUser


class FacultyUser(AbstractDomainUser):
    """Engineering Faculty Recruitment domain user (professors, colleges)."""

    email_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Faculty User"
        verbose_name_plural = "Faculty Users"
        db_table = "accounts_faculty_user"

    @property
    def domain(self):
        return "faculty"
