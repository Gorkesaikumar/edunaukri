from apps.audit.services.audit_service import AuditService
from apps.colleges.constants.enums import CollegeMemberRole
from apps.colleges.models import College
from apps.colleges.repositories.college_repository import (
    CollegeMemberRepository,
    InstitutionRepository,
)
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.colleges.validators.college_validators import (
    validate_accreditation_number,
    validate_established_year,
    validate_institution_email,
    validate_institution_phone,
    validate_institution_website,
    validate_latitude,
    validate_longitude,
    validate_postal_code,
    validate_social_link,
)
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    PermissionDeniedException,
)
from apps.core.services.base import BaseService
from apps.core.services.validation import ValidationService
from apps.core.utils.strings import slugify

WRITABLE_FIELDS = (
    "name",
    "legal_name",
    "college_type",
    "institution_type",
    "ownership_type",
    "autonomous_status",
    "description",
    "vision",
    "mission",
    "infrastructure_description",
    "facilities",
    "placement_cell_details",
    "research_centers",
    "hostel_availability",
    "transportation_facilities",
    "affiliated_university",
    "academic_calendar_reference",
    "programs_offered",
    "courses_offered",
    "accreditation",
    "aicte_code",
    "ugc_code",
    "naac_grade",
    "nba_accreditation",
    "established_year",
    "campus_area",
    "number_of_students",
    "number_of_faculty",
    "website_url",
    "contact_email",
    "contact_phone",
    "alternate_phone",
    "address_line",
    "city",
    "district",
    "state",
    "country",
    "pin_code",
    "latitude",
    "longitude",
    "linkedin_url",
    "facebook_url",
    "instagram_url",
    "twitter_url",
    "youtube_url",
    "profile_visibility",
)

SOCIAL_FIELDS = (
    "linkedin_url",
    "facebook_url",
    "instagram_url",
    "twitter_url",
    "youtube_url",
)


class InstitutionService(BaseService):
    """Business logic for institution lifecycle management (academic domain)."""

    def __init__(self):
        self.institution_repo = InstitutionRepository()
        self.member_repo = CollegeMemberRepository()
        self.member_selector = CollegeMemberSelector()
        self.validation = ValidationService()
        self.audit = AuditService()

    @BaseService.atomic
    def create_institution(self, *, college_user, data: dict) -> College:
        name = data.get("name")
        if not name:
            raise BusinessLogicException("Institution name is required.")

        if self.member_selector.has_active_membership(college_user):
            raise ConflictException("College user already belongs to an institution.")

        slug = data.get("slug") or slugify(name)[:320]
        if self.institution_repo.exists(slug=slug):
            raise ConflictException("Institution slug already exists.")

        payload = self._clean_payload(data)
        institution = self.institution_repo.create(
            name=name,
            slug=slug,
            created_by_id=college_user.pk,
            **{k: v for k, v in payload.items() if k != "name"},
        )
        self.member_repo.create(
            college=institution,
            college_user=college_user,
            role=CollegeMemberRole.OWNER,
            is_primary=True,
            created_by_id=college_user.pk,
        )
        self._audit(
            institution,
            "institution.created",
            college_user.pk,
            {"name": institution.name},
        )
        return institution

    @BaseService.atomic
    def update_institution(
        self, *, institution: College, college_user, data: dict
    ) -> College:
        self._ensure_admin(college_user, institution)
        payload = self._clean_payload(data)
        if not payload:
            return institution
        institution = self.institution_repo.update(
            institution, updated_by_id=college_user.pk, **payload
        )
        self._audit(
            institution,
            "institution.updated",
            college_user.pk,
            {"fields": sorted(payload)},
        )
        return institution

    @BaseService.atomic
    def deactivate(self, *, institution: College, college_user) -> College:
        self._ensure_admin(college_user, institution)
        if not institution.is_active:
            return institution
        institution = self.institution_repo.update(
            institution, is_active=False, updated_by_id=college_user.pk
        )
        self._audit(institution, "institution.deactivated", college_user.pk, {})
        return institution

    @BaseService.atomic
    def activate(self, *, institution: College, college_user) -> College:
        self._ensure_admin(college_user, institution)
        if institution.is_active:
            return institution
        institution = self.institution_repo.update(
            institution, is_active=True, updated_by_id=college_user.pk
        )
        self._audit(institution, "institution.activated", college_user.pk, {})
        return institution

    @BaseService.atomic
    def soft_delete(self, *, institution: College, college_user) -> None:
        if not self.member_selector.is_owner(college_user, institution.pk):
            raise PermissionDeniedException(
                "Only the institution owner can delete this institution."
            )
        institution.deleted_by_id = college_user.pk
        institution.save(update_fields=["deleted_by_id"])
        self.institution_repo.soft_delete(institution)
        self._audit(institution, "institution.deleted", college_user.pk, {})

    def assert_can_publish_vacancies(self, institution: College) -> None:
        """Guard used by the Faculty Vacancy module before publishing."""
        if not institution.can_publish_vacancies:
            raise BusinessLogicException(
                "Only active, verified institutions can publish faculty vacancies."
            )

    def _ensure_admin(self, college_user, institution: College) -> None:
        if not self.member_selector.is_admin(college_user, institution.pk):
            raise PermissionDeniedException(
                "Only institution administrators can manage this institution."
            )

    def _clean_payload(self, data: dict) -> dict:
        payload = {key: data[key] for key in WRITABLE_FIELDS if key in data}

        if payload.get("website_url"):
            self.validation.validate(
                validator=validate_institution_website, value=payload["website_url"]
            )
        if payload.get("contact_email"):
            self.validation.validate(
                validator=validate_institution_email, value=payload["contact_email"]
            )
        for phone_field in ("contact_phone", "alternate_phone"):
            if payload.get(phone_field):
                self.validation.validate(
                    validator=validate_institution_phone, value=payload[phone_field]
                )
        if payload.get("pin_code"):
            self.validation.validate(
                validator=validate_postal_code, value=payload["pin_code"]
            )
        if "established_year" in payload and payload["established_year"] is not None:
            self.validation.validate(
                validator=validate_established_year, value=payload["established_year"]
            )
        for accr_field, label in (
            ("aicte_code", "AICTE approval number"),
            ("ugc_code", "UGC recognition number"),
            ("nba_accreditation", "NBA accreditation"),
        ):
            if payload.get(accr_field):
                self.validation.validate(
                    validator=validate_accreditation_number,
                    value=payload[accr_field],
                    label=label,
                )
        if payload.get("latitude") is not None:
            self.validation.validate(
                validator=validate_latitude, value=payload["latitude"]
            )
        if payload.get("longitude") is not None:
            self.validation.validate(
                validator=validate_longitude, value=payload["longitude"]
            )
        for field in SOCIAL_FIELDS:
            if payload.get(field):
                self.validation.validate(
                    validator=validate_social_link, value=payload[field], field=field
                )

        return payload

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
