from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.services.audit_service import AuditService
from apps.colleges.models import College
from apps.colleges.repositories.college_repository import InstitutionRepository
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.colleges.validators.college_validators import (
    validate_banner_file,
    validate_logo_file,
)
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    PermissionDeniedException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.documents.selectors.stored_file_selector import StoredFileSelector
from apps.documents.services.file_access_service import FileAccessService


class InstitutionBrandingService(BaseService):
    """Manages institution logo and cover banner assets."""

    def __init__(self):
        self.institution_repo = InstitutionRepository()
        self.member_selector = CollegeMemberSelector()
        self.file_selector = StoredFileSelector()
        self.file_access = FileAccessService()
        self.audit = AuditService()

    @BaseService.atomic
    def set_logo(
        self, *, institution: College, college_user, user, logo_file_id
    ) -> College:
        self._ensure_admin(college_user, institution)
        stored = self._resolve_file(
            user=user, file_id=logo_file_id, validator=validate_logo_file
        )
        institution = self.institution_repo.update(
            institution, logo_file=stored, updated_by_id=college_user.pk
        )
        self._audit(
            institution,
            "institution.logo_updated",
            college_user.pk,
            {"logo_file_id": str(stored.pk)},
        )
        return institution

    @BaseService.atomic
    def set_banner(
        self, *, institution: College, college_user, user, banner_file_id
    ) -> College:
        self._ensure_admin(college_user, institution)
        stored = self._resolve_file(
            user=user, file_id=banner_file_id, validator=validate_banner_file
        )
        institution = self.institution_repo.update(
            institution, cover_banner_file=stored, updated_by_id=college_user.pk
        )
        self._audit(
            institution,
            "institution.banner_updated",
            college_user.pk,
            {"banner_file_id": str(stored.pk)},
        )
        return institution

    def _resolve_file(self, *, user, file_id, validator):
        stored = self.file_selector.get_active(file_id)
        if not stored:
            raise ValidationException("Branding file not found.")
        try:
            self.file_access.assert_can_access(user=user, stored_file=stored)
        except PermissionDenied as exc:
            raise ValidationException(str(exc)) from exc
        try:
            validator(stored)
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid branding file."
            ) from exc
        return stored

    def _ensure_admin(self, college_user, institution: College) -> None:
        if not self.member_selector.is_admin(college_user, institution.pk):
            raise PermissionDeniedException(
                "Only institution administrators can manage branding."
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
