from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.managers import AllObjectsManager, DomainUserManager
from apps.core.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AbstractDomainUser(
    AbstractBaseUser,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    """Abstract base user shared across Admin, IT, and Faculty domains."""

    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    account_status = models.CharField(
        max_length=30,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = DomainUserManager()
    all_objects = AllObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        abstract = True

    def __str__(self):
        return self.email

    @property
    def domain(self):
        raise NotImplementedError("Subclasses must define a domain property.")

    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > timezone.now()

    @property
    def is_staff(self) -> bool:
        """Domain users (IT, faculty, etc.) are not Django admin staff."""
        return False

    @property
    def is_superuser(self) -> bool:
        return False

    def record_failed_login(self, *, lock_after: int, lock_minutes: int) -> None:
        self.failed_login_attempts += 1
        update_fields = ["failed_login_attempts", "updated_at"]
        if self.failed_login_attempts >= lock_after:
            self.locked_until = timezone.now() + timezone.timedelta(
                minutes=lock_minutes
            )
            update_fields.append("locked_until")
        self.save(update_fields=update_fields)

    def reset_login_attempts(self) -> None:
        if self.failed_login_attempts or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(
                update_fields=["failed_login_attempts", "locked_until", "updated_at"]
            )
