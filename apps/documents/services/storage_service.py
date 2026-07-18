import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.documents.constants.enums import (
    StorageBackendType,
    StorageFileStatus,
    StorageFileType,
)
from apps.documents.models import StoredFile
from apps.documents.repositories.stored_file import StoredFileRepository
from apps.documents.validators.upload import UploadValidator, sanitize_original_filename

FILE_TYPE_PATH_MAP = {
    StorageFileType.RESUME: "it/resumes",
    StorageFileType.CV: "faculty/cvs",
    StorageFileType.CERTIFICATE: "it/certificates",
    StorageFileType.PROFILE_PHOTO: "it/profile-photos",
    StorageFileType.COMPANY_LOGO: "it/companies/logos",
    StorageFileType.COLLEGE_LOGO: "faculty/colleges/logos",
    StorageFileType.COLLEGE_BANNER: "faculty/colleges/banners",
    StorageFileType.INVOICE_PDF: "billing/invoices",
    StorageFileType.CLAIM_DOCUMENT: "billing/claims",
    StorageFileType.OTHER: "admin/exports",
}


class StorageService(BaseService):
    """Handle validated file uploads and metadata registration."""

    def __init__(self, repository=None):
        self.repository = repository or StoredFileRepository()

    def upload(
        self,
        *,
        uploaded_file: UploadedFile,
        domain: str,
        file_type: str,
        owner_type: str,
        owner_id,
        uploaded_by_id,
    ) -> StoredFile:
        UploadValidator.validate(uploaded_file=uploaded_file, file_type=file_type)

        safe_original_name = sanitize_original_filename(uploaded_file.name)
        stored_filename = StoredFile.generate_stored_filename(safe_original_name)
        relative_dir = self._build_relative_dir(domain, file_type, owner_id)
        relative_path = f"{relative_dir}/{stored_filename}"
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path

        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        checksum = self._write_file_and_checksum(uploaded_file, absolute_path)

        stored_file = self.repository.create(
            domain=domain,
            file_type=file_type,
            original_filename=safe_original_name,
            stored_filename=stored_filename,
            storage_path=relative_path.replace("\\", "/"),
            storage_backend=StorageBackendType.LOCAL,
            mime_type=getattr(
                uploaded_file, "content_type", "application/octet-stream"
            ),
            file_size_bytes=uploaded_file.size,
            checksum_sha256=checksum,
            owner_type=owner_type,
            owner_id=owner_id,
            status=StorageFileStatus.ACTIVE,
            uploaded_by_id=uploaded_by_id,
        )

        from apps.audit.services.audit_service import AuditService

        AuditService().record(
            domain=domain,
            event_type="file.uploaded",
            entity_type="stored_file",
            entity_id=stored_file.id,
            payload={"file_type": file_type, "filename": uploaded_file.name},
            actor_id=uploaded_by_id,
        )

        return stored_file

    def get_absolute_path(self, stored_file: StoredFile) -> Path:
        return Path(settings.MEDIA_ROOT) / stored_file.storage_path

    def remove_stored_file(self, stored_file: StoredFile) -> None:
        """Delete physical file and soft-delete metadata."""
        if not stored_file:
            return
        try:
            absolute_path = self.get_absolute_path(stored_file)
            if absolute_path.is_file():
                absolute_path.unlink()
        except OSError:
            pass
        self.repository.soft_delete(stored_file)

    def _build_relative_dir(self, domain: str, file_type: str, owner_id) -> str:
        base = FILE_TYPE_PATH_MAP.get(file_type, f"{domain}/files")
        return f"{base}/{owner_id}"

    def _write_file_and_checksum(
        self, uploaded_file: UploadedFile, absolute_path: Path
    ) -> str:
        sha256 = hashlib.sha256()
        with absolute_path.open("wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
                sha256.update(chunk)
        return sha256.hexdigest()
