from django.core.exceptions import PermissionDenied

from apps.audit.services.audit_service import AuditService
from apps.companies.models import Company
from apps.companies.repositories.company_repository import CompanyRepository
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.companies.validators.company_validators import (
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
from apps.it_recruitment.models import RecruiterProfile


class CompanyBrandingService(BaseService):
    """Manages company logo and cover banner assets."""

    def __init__(self):
        self.company_repo = CompanyRepository()
        self.member_selector = CompanyMemberSelector()
        self.file_selector = StoredFileSelector()
        self.file_access = FileAccessService()
        self.audit = AuditService()

    @BaseService.atomic
    def set_logo(
        self, *, company: Company, recruiter: RecruiterProfile, user, logo_file_id
    ) -> Company:
        stored = self._resolve_file(
            user=user, file_id=logo_file_id, validator=validate_logo_file
        )
        self._ensure_member(recruiter, company)
        company = self.company_repo.update(
            company, logo_file=stored, updated_by_id=recruiter.user_id
        )
        self._audit(
            company,
            "company.logo_updated",
            recruiter.user_id,
            {"logo_file_id": str(stored.pk)},
        )
        return company

    @BaseService.atomic
    def set_banner(
        self, *, company: Company, recruiter: RecruiterProfile, user, banner_file_id
    ) -> Company:
        stored = self._resolve_file(
            user=user, file_id=banner_file_id, validator=validate_banner_file
        )
        self._ensure_member(recruiter, company)
        company = self.company_repo.update(
            company, cover_banner_file=stored, updated_by_id=recruiter.user_id
        )
        self._audit(
            company,
            "company.banner_updated",
            recruiter.user_id,
            {"banner_file_id": str(stored.pk)},
        )
        return company

    def _resolve_file(self, *, user, file_id, validator):
        stored = self.file_selector.get_active(file_id)
        if not stored:
            raise ValidationException("Branding file not found.")
        try:
            self.file_access.assert_can_access(user=user, stored_file=stored)
        except PermissionDenied as exc:
            raise ValidationException(str(exc)) from exc
        self.validation_check(stored, validator)
        return stored

    def validation_check(self, stored, validator) -> None:
        from django.core.exceptions import ValidationError

        try:
            validator(stored)
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid branding file."
            ) from exc

    def _ensure_member(self, recruiter: RecruiterProfile, company: Company) -> None:
        if not self.member_selector.is_member(recruiter, company.pk):
            raise PermissionDeniedException("You are not a member of this company.")

    def _audit(
        self, company: Company, event_type: str, actor_id, payload: dict
    ) -> None:
        self.audit.record(
            domain=DomainType.IT,
            event_type=event_type,
            entity_type=EntityReferenceType.IT_COMPANY,
            entity_id=company.pk,
            payload=payload,
            actor_type=ActorType.IT_USER,
            actor_id=actor_id,
        )
