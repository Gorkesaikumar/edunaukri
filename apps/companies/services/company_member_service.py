from apps.audit.services.audit_service import AuditService
from apps.companies.constants.enums import CompanyMemberRole
from apps.companies.models import Company, CompanyMember
from apps.companies.repositories.company_repository import CompanyMemberRepository
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector


class CompanyMemberService(BaseService):
    """Manages the recruiters authorized to act on behalf of a company."""

    def __init__(self):
        self.member_repo = CompanyMemberRepository()
        self.member_selector = CompanyMemberSelector()
        self.recruiter_selector = RecruiterProfileSelector()
        self.audit = AuditService()
        self.outbox = OutboxService()

    @BaseService.atomic
    def add_member(
        self,
        *,
        company: Company,
        actor: RecruiterProfile,
        recruiter_email: str,
        role: str = CompanyMemberRole.RECRUITER,
    ) -> CompanyMember:
        self._ensure_owner(actor, company)

        target = self._resolve_recruiter(recruiter_email)
        if self.member_selector.for_recruiter(target).exists():
            raise ConflictException("Recruiter already belongs to a company.")
        if role == CompanyMemberRole.OWNER:
            raise BusinessLogicException("A company can only have one owner.")

        member = self.member_repo.create(
            company=company,
            recruiter=target,
            role=role,
            is_primary=False,
            created_by_id=actor.user_id,
        )
        self._audit(
            company,
            "company.member_added",
            actor.user_id,
            {"recruiter_id": str(target.pk), "role": role},
        )
        self.outbox.publish(
            domain=DomainType.IT,
            event_type="company.member_added",
            aggregate_type="it_company",
            aggregate_id=company.pk,
            payload={
                "recipient_domain": "it",
                "recipient_id": str(target.user_id),
                "title": "Added to a company",
                "body": f"You have been added to {company.name} as {role}.",
            },
        )
        return member

    @BaseService.atomic
    def remove_member(
        self, *, company: Company, actor: RecruiterProfile, member_id
    ) -> None:
        self._ensure_owner(actor, company)
        member = (
            self.member_selector.for_company(company.pk).filter(pk=member_id).first()
        )
        if not member:
            raise ResourceNotFoundException("Company member not found.")
        if member.role == CompanyMemberRole.OWNER:
            raise BusinessLogicException("The company owner cannot be removed.")
        self.member_repo.update(member, is_active=False, updated_by_id=actor.user_id)
        self._audit(
            company,
            "company.member_removed",
            actor.user_id,
            {"member_id": str(member_id)},
        )

    def _resolve_recruiter(self, recruiter_email: str) -> RecruiterProfile:
        from apps.accounts.models import ITUser

        user = ITUser.objects.filter(email__iexact=recruiter_email).first()
        recruiter = self.recruiter_selector.for_user(user) if user else None
        if not recruiter:
            raise ResourceNotFoundException(
                "No recruiter profile found for that email."
            )
        return recruiter

    def _ensure_owner(self, actor: RecruiterProfile, company: Company) -> None:
        if not self.member_selector.is_owner(actor, company.pk):
            raise PermissionDeniedException(
                "Only the company owner can manage members."
            )

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
