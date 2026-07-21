from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.companies.constants.enums import CompanyMemberRole
from apps.companies.models import Company
from apps.companies.repositories.company_repository import (
    CompanyMemberRepository,
    CompanyRepository,
)
from apps.companies.selectors.company_selector import (
    CompanyMemberSelector,
    CompanySelector,
)
from apps.companies.validators.company_validators import (
    validate_company_email,
    validate_company_phone,
    validate_company_website,
    validate_founded_year,
    validate_gst_number,
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
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.models import JobPosting
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.jobs.selectors.job_selector import JobPostingSelector

WRITABLE_FIELDS = (
    "name",
    "legal_name",
    "description",
    "mission",
    "vision",
    "benefits",
    "culture",
    "industry",
    "organization_type",
    "company_size",
    "founded_year",
    "gst_number",
    "website_url",
    "email",
    "phone",
    "headquarters_location",
    "address_line",
    "city",
    "state",
    "country",
    "postal_code",
    "linkedin_url",
    "twitter_url",
    "facebook_url",
    "instagram_url",
    "youtube_url",
)

SOCIAL_FIELDS = (
    "linkedin_url",
    "twitter_url",
    "facebook_url",
    "instagram_url",
    "youtube_url",
)


class CompanyService(BaseService):
    """Business logic for company lifecycle management (IT domain)."""

    def __init__(self):
        self.company_repo = CompanyRepository()
        self.member_repo = CompanyMemberRepository()
        self.company_selector = CompanySelector()
        self.member_selector = CompanyMemberSelector()
        self.validation = ValidationService()
        self.audit = AuditService()

    # ---------------------------------------------------------------- create
    @BaseService.atomic
    def create_company(self, *, recruiter: RecruiterProfile, data: dict) -> Company:
        name = data.get("name")
        if not name:
            raise BusinessLogicException("Company name is required.")

        if self.member_selector.for_recruiter(recruiter).exists():
            raise ConflictException("Recruiter already belongs to a company.")

        slug = data.get("slug") or slugify(name)[:320]
        if self.company_repo.exists(slug=slug):
            raise ConflictException("A company with this name already exists.")

        payload = self._clean_payload(data, existing=None)
        company = self.company_repo.create(
            name=name,
            slug=slug,
            created_by_id=recruiter.user_id,
            **{k: v for k, v in payload.items() if k != "name"},
        )
        self.member_repo.create(
            company=company,
            recruiter=recruiter,
            role=CompanyMemberRole.OWNER,
            is_primary=True,
            created_by_id=recruiter.user_id,
        )
        self._audit(
            company, "company.created", recruiter.user_id, {"name": company.name}
        )
        return company

    # ---------------------------------------------------------------- update
    @BaseService.atomic
    def update_company(
        self, *, company: Company, recruiter: RecruiterProfile, data: dict
    ) -> Company:
        self._ensure_member(recruiter, company)
        payload = self._clean_payload(data, existing=company)
        if not payload:
            return company
        company = self.company_repo.update(
            company, updated_by_id=recruiter.user_id, **payload
        )
        self._audit(
            company, "company.updated", recruiter.user_id, {"fields": sorted(payload)}
        )
        return company

    # ------------------------------------------------------------- lifecycle
    @BaseService.atomic
    def deactivate(self, *, company: Company, recruiter: RecruiterProfile) -> Company:
        self._ensure_member(recruiter, company)
        if not company.is_active:
            return company
        company = self.company_repo.update(
            company, is_active=False, updated_by_id=recruiter.user_id
        )
        self._audit(company, "company.deactivated", recruiter.user_id, {})
        return company

    @BaseService.atomic
    def activate(self, *, company: Company, recruiter: RecruiterProfile) -> Company:
        self._ensure_member(recruiter, company)
        if company.is_active:
            return company
        company = self.company_repo.update(
            company, is_active=True, updated_by_id=recruiter.user_id
        )
        self._audit(company, "company.activated", recruiter.user_id, {})
        return company

    @BaseService.atomic
    def soft_delete(self, *, company: Company, recruiter: RecruiterProfile) -> None:
        if not self.member_selector.is_owner(recruiter, company.pk):
            raise PermissionDeniedException(
                "Only the company owner can delete this company."
            )
        company.deleted_by_id = recruiter.user_id
        company.save(update_fields=["deleted_by_id"])
        self.company_repo.soft_delete(company)
        self._audit(company, "company.deleted", recruiter.user_id, {})

    # --------------------------------------------------------------- helpers
    def assert_can_publish_jobs(self, company: Company) -> None:
        """Guard used by the Jobs module before publishing a posting."""
        if not company.can_publish_jobs:
            raise BusinessLogicException(
                "Only active, verified companies can publish jobs."
            )

    def _ensure_member(self, recruiter: RecruiterProfile, company: Company) -> None:
        if not self.member_selector.is_member(recruiter, company.pk):
            raise PermissionDeniedException("You are not a member of this company.")

    def _clean_payload(self, data: dict, *, existing: Company | None) -> dict:
        payload = {key: data[key] for key in WRITABLE_FIELDS if key in data}

        website = payload.get("website_url")
        if website:
            self.validation.validate(validator=validate_company_website, value=website)

        email = payload.get("email")
        if email:
            self.validation.validate(validator=validate_company_email, value=email)

        phone = payload.get("phone")
        if phone:
            self.validation.validate(validator=validate_company_phone, value=phone)

        gst = payload.get("gst_number")
        if gst:
            self.validation.validate(validator=validate_gst_number, value=gst)

        if "founded_year" in payload and payload["founded_year"] is not None:
            self.validation.validate(
                validator=validate_founded_year, value=payload["founded_year"]
            )

        for field in SOCIAL_FIELDS:
            value = payload.get(field)
            if value:
                self.validation.validate(
                    validator=validate_social_link, value=value, field=field
                )

        return payload

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


class JobPostingService(BaseService):
    def __init__(self):
        self.job_repo = JobPostingRepository()
        self.job_selector = JobPostingSelector()

    @BaseService.atomic
    def create_published_job(
        self, *, company: Company, recruiter: RecruiterProfile, data: dict
    ) -> JobPosting:
        from apps.jobs.services.job_service import JobService
        from apps.jobs.services.job_publication_service import JobPublicationService

        payload = dict(data)
        payload["company_id"] = company.pk
        if (
            not payload.get("city")
            and not payload.get("country")
            and payload.get("location")
        ):
            payload["city"] = payload["location"]
        
        job = JobService().create_job(recruiter=recruiter, data=payload)
        return JobPublicationService().publish(job_posting=job, recruiter=recruiter)

    @BaseService.atomic
    def publish(
        self, job_posting: JobPosting, *, recruiter: RecruiterProfile
    ) -> JobPosting:
        from apps.jobs.services.job_publication_service import JobPublicationService

        return JobPublicationService().publish(
            job_posting=job_posting, recruiter=recruiter
        )

    @BaseService.atomic
    def update_draft(
        self, job_posting: JobPosting, *, recruiter: RecruiterProfile, data: dict
    ) -> JobPosting:
        from apps.jobs.services.job_service import JobService

        payload = dict(data)
        if (
            not payload.get("city")
            and not payload.get("country")
            and payload.get("location")
        ):
            payload["city"] = payload["location"]
        if not payload.get("city") and not payload.get("country"):
            if job_posting.city or job_posting.location:
                payload.setdefault("city", job_posting.city or job_posting.location)
            if job_posting.country:
                payload.setdefault("country", job_posting.country)
        return JobService().update_job(
            job_posting=job_posting, recruiter=recruiter, data=payload
        )

    @BaseService.atomic
    def close(
        self, job_posting: JobPosting, *, recruiter: RecruiterProfile
    ) -> JobPosting:
        from apps.jobs.services.job_lifecycle_service import JobLifecycleService

        return JobLifecycleService().close(job_posting=job_posting, recruiter=recruiter)

    def _ensure_recruiter_owns_job(
        self, job_posting: JobPosting, recruiter: RecruiterProfile
    ) -> None:
        if not CompanyMemberSelector().is_member(recruiter, job_posting.company_id):
            raise BusinessLogicException("You do not manage this job posting.")
