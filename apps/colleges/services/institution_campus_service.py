from apps.audit.services.audit_service import AuditService
from apps.colleges.models import College, InstitutionCampus
from apps.colleges.repositories.college_repository import InstitutionCampusRepository
from apps.colleges.selectors.college_selector import (
    CollegeMemberSelector,
    InstitutionCampusSelector,
)
from apps.colleges.validators.college_validators import (
    validate_latitude,
    validate_longitude,
    validate_postal_code,
)
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService
from apps.core.services.validation import ValidationService

CAMPUS_FIELDS = (
    "label",
    "address_line",
    "city",
    "district",
    "state",
    "country",
    "pin_code",
    "latitude",
    "longitude",
    "is_main_campus",
)


class InstitutionCampusService(BaseService):
    """Manages additional campuses for multi-campus institutions."""

    def __init__(self):
        self.campus_repo = InstitutionCampusRepository()
        self.campus_selector = InstitutionCampusSelector()
        self.member_selector = CollegeMemberSelector()
        self.validation = ValidationService()
        self.audit = AuditService()

    @BaseService.atomic
    def add_campus(
        self, *, institution: College, college_user, data: dict
    ) -> InstitutionCampus:
        self._ensure_admin(college_user, institution)
        payload = self._clean(data)
        campus = self.campus_repo.create(
            college=institution, created_by_id=college_user.pk, **payload
        )
        if campus.is_main_campus:
            self._demote_other_main(institution, keep_id=campus.pk)
        self._audit(
            institution,
            "institution.campus_added",
            college_user.pk,
            {"campus_id": str(campus.pk)},
        )
        return campus

    @BaseService.atomic
    def update_campus(
        self, *, institution: College, college_user, campus_id, data: dict
    ) -> InstitutionCampus:
        self._ensure_admin(college_user, institution)
        campus = self._get_campus(institution, campus_id)
        payload = self._clean(data)
        if payload:
            campus = self.campus_repo.update(
                campus, updated_by_id=college_user.pk, **payload
            )
        if campus.is_main_campus:
            self._demote_other_main(institution, keep_id=campus.pk)
        self._audit(
            institution,
            "institution.campus_updated",
            college_user.pk,
            {"campus_id": str(campus.pk)},
        )
        return campus

    @BaseService.atomic
    def delete_campus(self, *, institution: College, college_user, campus_id) -> None:
        self._ensure_admin(college_user, institution)
        campus = self._get_campus(institution, campus_id)
        self.campus_repo.soft_delete(campus)
        self._audit(
            institution,
            "institution.campus_removed",
            college_user.pk,
            {"campus_id": str(campus_id)},
        )

    def _clean(self, data: dict) -> dict:
        payload = {key: data[key] for key in CAMPUS_FIELDS if key in data}
        if payload.get("pin_code"):
            self.validation.validate(
                validator=validate_postal_code, value=payload["pin_code"]
            )
        if payload.get("latitude") is not None:
            self.validation.validate(
                validator=validate_latitude, value=payload["latitude"]
            )
        if payload.get("longitude") is not None:
            self.validation.validate(
                validator=validate_longitude, value=payload["longitude"]
            )
        return payload

    def _get_campus(self, institution: College, campus_id) -> InstitutionCampus:
        campus = (
            self.campus_selector.for_college(institution.pk)
            .filter(pk=campus_id)
            .first()
        )
        if not campus:
            raise ResourceNotFoundException("Campus not found.")
        return campus

    def _demote_other_main(self, institution: College, *, keep_id) -> None:
        InstitutionCampus.objects.filter(
            college_id=institution.pk, is_main_campus=True
        ).exclude(pk=keep_id).update(is_main_campus=False)

    def _ensure_admin(self, college_user, institution: College) -> None:
        if not self.member_selector.is_admin(college_user, institution.pk):
            raise PermissionDeniedException(
                "Only institution administrators can manage campuses."
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
