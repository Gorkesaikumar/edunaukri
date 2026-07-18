from django.core.exceptions import PermissionDenied

from apps.audit.services.audit_service import AuditService
from apps.colleges.models import College, InstitutionDocument
from apps.colleges.repositories.college_repository import InstitutionDocumentRepository
from apps.colleges.selectors.college_selector import (
    CollegeMemberSelector,
    InstitutionDocumentSelector,
)
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.documents.constants.enums import StorageFileStatus
from apps.documents.selectors.stored_file_selector import StoredFileSelector
from apps.documents.services.file_access_service import FileAccessService


class InstitutionDocumentService(BaseService):
    """Attaches approval / accreditation / branding documents to institutions."""

    def __init__(self):
        self.document_repo = InstitutionDocumentRepository()
        self.document_selector = InstitutionDocumentSelector()
        self.member_selector = CollegeMemberSelector()
        self.file_selector = StoredFileSelector()
        self.file_access = FileAccessService()
        self.audit = AuditService()

    @BaseService.atomic
    def attach_document(
        self,
        *,
        institution: College,
        college_user,
        user,
        document_type: str,
        stored_file_id,
        title: str = "",
    ) -> InstitutionDocument:
        self._ensure_admin(college_user, institution)
        stored = self.file_selector.get_active(stored_file_id)
        if not stored:
            raise ValidationException("Document file not found.")
        try:
            self.file_access.assert_can_access(user=user, stored_file=stored)
        except PermissionDenied as exc:
            raise ValidationException(str(exc)) from exc
        if stored.status != StorageFileStatus.ACTIVE:
            raise ValidationException("Document file is not available.")

        document = self.document_repo.create(
            college=institution,
            document_type=document_type,
            stored_file=stored,
            title=title or "",
            created_by_id=college_user.pk,
        )
        self._audit(
            institution,
            "institution.document_added",
            college_user.pk,
            {"document_id": str(document.pk), "document_type": document_type},
        )
        return document

    @BaseService.atomic
    def remove_document(
        self, *, institution: College, college_user, document_id
    ) -> None:
        self._ensure_admin(college_user, institution)
        document = (
            self.document_selector.for_college(institution.pk)
            .filter(pk=document_id)
            .first()
        )
        if not document:
            raise ResourceNotFoundException("Institution document not found.")
        self.document_repo.soft_delete(document)
        self._audit(
            institution,
            "institution.document_removed",
            college_user.pk,
            {"document_id": str(document_id)},
        )

    def _ensure_admin(self, college_user, institution: College) -> None:
        if not self.member_selector.is_admin(college_user, institution.pk):
            raise PermissionDeniedException(
                "Only institution administrators can manage documents."
            )

    def _audit(
        self, institution: College, event_type: str, actor_id, payload: dict
    ) -> None:
        self.audit.record(
            domain=DomainType.FACULTY,
            event_type=event_type,
            entity_type=EntityReferenceType.FACULTY_COLLEGE,
            entity_id=institution.pk,
            payload=payload,
            actor_type=ActorType.COLLEGE,
            actor_id=actor_id,
        )
