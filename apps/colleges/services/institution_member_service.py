from apps.audit.services.audit_service import AuditService
from apps.colleges.constants.enums import CollegeMemberRole
from apps.colleges.models import College, CollegeMember
from apps.colleges.repositories.college_repository import CollegeMemberRepository
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService


class InstitutionMemberService(BaseService):
    """Manages the college users authorized to act for an institution."""

    def __init__(self):
        self.member_repo = CollegeMemberRepository()
        self.member_selector = CollegeMemberSelector()
        self.audit = AuditService()
        self.outbox = OutboxService()

    @BaseService.atomic
    def add_member(
        self,
        *,
        institution: College,
        actor,
        user_email: str,
        role: str = CollegeMemberRole.MEMBER,
    ) -> CollegeMember:
        self._ensure_admin(actor, institution)

        target = self._resolve_college_user(user_email)
        if self.member_selector.has_active_membership(target):
            raise ConflictException("College user already belongs to an institution.")
        if role == CollegeMemberRole.OWNER:
            raise BusinessLogicException("An institution can only have one owner.")

        member = self.member_repo.create(
            college=institution,
            college_user=target,
            role=role,
            is_primary=False,
            created_by_id=actor.pk,
        )
        self._audit(
            institution,
            "institution.member_added",
            actor.pk,
            {"college_user_id": str(target.pk), "role": role},
        )
        self.outbox.publish(
            domain=DomainType.FACULTY,
            event_type="institution.member_added",
            aggregate_type="faculty_college",
            aggregate_id=institution.pk,
            payload={
                "recipient_domain": "college",
                "recipient_id": str(target.pk),
                "title": "Added to an institution",
                "body": f"You have been added to {institution.name} as {role}.",
            },
        )
        return member

    @BaseService.atomic
    def remove_member(self, *, institution: College, actor, member_id) -> None:
        self._ensure_admin(actor, institution)
        member = (
            self.member_selector.for_college(institution.pk)
            .filter(pk=member_id)
            .first()
        )
        if not member:
            raise ResourceNotFoundException("Institution member not found.")
        if member.role == CollegeMemberRole.OWNER:
            raise BusinessLogicException("The institution owner cannot be removed.")
        self.member_repo.update(member, is_active=False, updated_by_id=actor.pk)
        self._audit(
            institution,
            "institution.member_removed",
            actor.pk,
            {"member_id": str(member_id)},
        )

    def _resolve_college_user(self, user_email: str):
        from apps.accounts.models import CollegeUser

        user = CollegeUser.objects.filter(email__iexact=user_email).first()
        if not user:
            raise ResourceNotFoundException("No college user found for that email.")
        return user

    def _ensure_admin(self, actor, institution: College) -> None:
        if not self.member_selector.is_admin(actor, institution.pk):
            raise PermissionDeniedException(
                "Only institution administrators can manage members."
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
