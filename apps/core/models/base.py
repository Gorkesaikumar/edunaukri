from apps.core.models.audit import AuditFieldsMixin
from apps.core.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Abstract base model for all domain entities."""

    class Meta:
        abstract = True


class AuditedBaseModel(AuditFieldsMixin, BaseModel):
    """Base model with full audit trail columns."""

    class Meta:
        abstract = True
