import uuid

from django.db import models

from apps.core.validators.common import validate_clean_text
from apps.core.constants.enums import DomainType
from apps.core.models.base import BaseModel
from apps.documents.constants.enums import (
    StorageBackendType,
    StorageFileStatus,
    StorageFileType,
)


class StoredFile(BaseModel):
    """Metadata record for every uploaded file in the platform."""

    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    file_type = models.CharField(
        max_length=30, choices=StorageFileType.choices, db_index=True
    )
    original_filename = models.CharField(max_length=500, validators=[validate_clean_text])
    stored_filename = models.CharField(max_length=500, validators=[validate_clean_text])
    storage_path = models.CharField(max_length=1000)
    storage_backend = models.CharField(
        max_length=50,
        choices=StorageBackendType.choices,
        default=StorageBackendType.LOCAL,
    )
    mime_type = models.CharField(max_length=100)
    file_size_bytes = models.BigIntegerField()
    checksum_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    owner_type = models.CharField(max_length=50, db_index=True)
    owner_id = models.UUIDField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=StorageFileStatus.choices,
        default=StorageFileStatus.ACTIVE,
        db_index=True,
    )
    parsed_data = models.JSONField(null=True, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    uploaded_by_id = models.UUIDField(db_index=True)

    class Meta:
        db_table = "storage_file"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["owner_type", "owner_id"], name="storage_file_owner_idx"
            ),
            models.Index(
                fields=["domain", "file_type"], name="storage_file_domain_type_idx"
            ),
        ]

    def __str__(self):
        return self.original_filename

    @staticmethod
    def generate_stored_filename(original_filename: str) -> str:
        extension = ""
        if "." in original_filename:
            extension = original_filename.rsplit(".", 1)[-1].lower()
        return f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
