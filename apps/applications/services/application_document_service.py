from django.core.exceptions import PermissionDenied, ValidationError

from apps.core.exceptions.domain_exceptions import ResumeRequiredException
from apps.core.services.base import BaseService
from apps.documents.constants.enums import StorageFileStatus, StorageFileType
from apps.documents.selectors.stored_file_selector import StoredFileSelector
from apps.documents.services.file_access_service import FileAccessService


class ApplicationDocumentService(BaseService):
    """Resolves resume/CV files for job and faculty applications."""

    def resolve_resume_for_seeker(self, *, seeker, user, resume_file_id=None):
        if resume_file_id:
            return self._resolve_file(
                file_id=resume_file_id,
                user=user,
                allowed_types={StorageFileType.RESUME},
                label="Resume",
            )
        return seeker.resume_file

    def resolve_cv_for_professor(self, *, professor, user, cv_file_id=None):
        if cv_file_id:
            return self._resolve_file(
                file_id=cv_file_id,
                user=user,
                allowed_types={StorageFileType.CV, StorageFileType.RESUME},
                label="CV",
            )
        return professor.cv_file

    def _resolve_file(self, *, file_id, user, allowed_types: set, label: str):
        stored = StoredFileSelector().get_active(file_id)
        if not stored:
            raise ResumeRequiredException(f"{label} file not found.")
        try:
            FileAccessService().assert_can_access(user=user, stored_file=stored)
        except PermissionDenied as exc:
            raise ResumeRequiredException(str(exc)) from exc
        if stored.status != StorageFileStatus.ACTIVE:
            raise ResumeRequiredException(f"{label} file is not available.")
        if stored.file_type not in allowed_types:
            raise ResumeRequiredException(f"Invalid {label.lower()} file type.")
        return stored
