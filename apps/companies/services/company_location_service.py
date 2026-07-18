from apps.audit.services.audit_service import AuditService
from apps.companies.models import Company, CompanyLocation
from apps.companies.repositories.company_repository import CompanyLocationRepository
from apps.companies.selectors.company_selector import (
    CompanyLocationSelector,
    CompanyMemberSelector,
)
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile

LOCATION_FIELDS = (
    "label",
    "address_line",
    "city",
    "state",
    "country",
    "postal_code",
    "is_headquarters",
)


class CompanyLocationService(BaseService):
    """Manages additional office locations for a company."""

    def __init__(self):
        self.location_repo = CompanyLocationRepository()
        self.location_selector = CompanyLocationSelector()
        self.member_selector = CompanyMemberSelector()
        self.audit = AuditService()

    @BaseService.atomic
    def add_location(
        self, *, company: Company, recruiter: RecruiterProfile, data: dict
    ) -> CompanyLocation:
        self._ensure_member(recruiter, company)
        payload = {key: data[key] for key in LOCATION_FIELDS if key in data}
        location = self.location_repo.create(
            company=company, created_by_id=recruiter.user_id, **payload
        )
        if location.is_headquarters:
            self._demote_other_headquarters(company, keep_id=location.pk)
        self._audit(
            company,
            "company.location_added",
            recruiter.user_id,
            {"location_id": str(location.pk)},
        )
        return location

    @BaseService.atomic
    def update_location(
        self, *, company: Company, recruiter: RecruiterProfile, location_id, data: dict
    ) -> CompanyLocation:
        self._ensure_member(recruiter, company)
        location = self._get_location(company, location_id)
        payload = {key: data[key] for key in LOCATION_FIELDS if key in data}
        if payload:
            location = self.location_repo.update(
                location, updated_by_id=recruiter.user_id, **payload
            )
        if location.is_headquarters:
            self._demote_other_headquarters(company, keep_id=location.pk)
        self._audit(
            company,
            "company.location_updated",
            recruiter.user_id,
            {"location_id": str(location.pk)},
        )
        return location

    @BaseService.atomic
    def delete_location(
        self, *, company: Company, recruiter: RecruiterProfile, location_id
    ) -> None:
        self._ensure_member(recruiter, company)
        location = self._get_location(company, location_id)
        self.location_repo.soft_delete(location)
        self._audit(
            company,
            "company.location_removed",
            recruiter.user_id,
            {"location_id": str(location_id)},
        )

    def _get_location(self, company: Company, location_id) -> CompanyLocation:
        location = (
            self.location_selector.for_company(company.pk)
            .filter(pk=location_id)
            .first()
        )
        if not location:
            raise ResourceNotFoundException("Company location not found.")
        return location

    def _demote_other_headquarters(self, company: Company, *, keep_id) -> None:
        CompanyLocation.objects.filter(
            company_id=company.pk, is_headquarters=True
        ).exclude(pk=keep_id).update(is_headquarters=False)

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
