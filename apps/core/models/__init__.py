from apps.core.models.audit import AuditFieldsMixin
from apps.core.models.base import AuditedBaseModel, BaseModel
from apps.core.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from apps.core.models.outbox_event import OutboxEvent
from apps.core.models.ownership import OwnershipModel
from apps.core.models.status import StatusModel

UUIDModel = UUIDPrimaryKeyMixin
TimeStampedModel = TimestampMixin
SoftDeleteModel = SoftDeleteMixin
AuditModel = AuditFieldsMixin

__all__ = [
    "BaseModel",
    "AuditedBaseModel",
    "UUIDPrimaryKeyMixin",
    "UUIDModel",
    "TimestampMixin",
    "TimeStampedModel",
    "SoftDeleteMixin",
    "SoftDeleteModel",
    "AuditFieldsMixin",
    "AuditModel",
    "StatusModel",
    "OwnershipModel",
    "OutboxEvent",
]
