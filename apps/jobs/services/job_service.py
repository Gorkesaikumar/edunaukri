import uuid

from apps.companies.selectors.company_selector import CompanySelector
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from apps.core.services.base import BaseService
from apps.core.utils.strings import slugify
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting, Skill
from apps.jobs.repositories.job_repository import (
    JobLocationRepository,
    JobPostingRepository,
    JobPostingSkillRepository,
)
from apps.jobs.services.base import JobServiceBase
from apps.jobs.services.job_validation_service import JobValidationService

WRITABLE_FIELDS = (
    "title",
    "job_code",
    "category",
    "department",
    "description",
    "requirements",
    "roles_responsibilities",
    "benefits",
    "education_requirement",
    "employment_type",
    "work_mode",
    "experience_min",
    "experience_max",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_visibility",
    "vacancies",
    "joining_timeline",
    "application_deadline",
    "hiring_manager",
    "country",
    "state",
    "city",
    "office_address",
    "location",
    "is_remote",
    "visibility",
    "is_template",
    "expires_at",
)

EDITABLE_STATUSES = (
    JobStatus.DRAFT,
    JobStatus.PENDING_APPROVAL,
    JobStatus.PUBLISHED,
    JobStatus.PAUSED,
)


class JobService(JobServiceBase):
    """Create, update, duplicate and delete job postings."""

    def __init__(self):
        super().__init__()
        self.job_repo = JobPostingRepository()
        self.skill_repo = JobPostingSkillRepository()
        self.location_repo = JobLocationRepository()
        self.company_selector = CompanySelector()
        self.validation = JobValidationService()

    @BaseService.atomic
    def create_job(self, *, recruiter, data: dict) -> JobPosting:
        self.validation.validate_payload(data, partial=False)

        company = self.company_selector.get_or_none(data.get("company_id"))
        if not company:
            raise ResourceNotFoundException("Company not found.")
        self._ensure_company_membership(company, recruiter)
        self._guard_duplicate(company, data["title"])

        payload = {
            key: data[key]
            for key in WRITABLE_FIELDS
            if key in data and data[key] is not None
        }
        payload.setdefault("work_mode", data.get("work_mode", "onsite"))
        payload.setdefault("vacancies", 1)
        payload["is_remote"] = payload.get("work_mode") == "remote" or bool(
            payload.get("is_remote")
        )

        job = self.job_repo.create(
            company=company,
            posted_by=recruiter,
            slug=self._unique_slug(company, data["title"]),
            company_name_snapshot=company.name,
            status=JobStatus.DRAFT,
            created_by_id=recruiter.user_id,
            **payload,
        )
        self._sync_skills(job, data, recruiter.user_id)
        self._sync_locations(job, data.get("locations"), recruiter.user_id)
        self._audit(job, "job.created", recruiter.user_id, {"title": job.title})
        return job

    @BaseService.atomic
    def update_job(
        self, *, job_posting: JobPosting, recruiter, data: dict
    ) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status not in EDITABLE_STATUSES:
            raise BusinessLogicException("This job can no longer be edited.")

        self.validation.validate_payload(data, partial=True)
        payload = {
            key: data[key]
            for key in WRITABLE_FIELDS
            if key in data and data[key] is not None
        }
        if "work_mode" in payload:
            payload["is_remote"] = payload["work_mode"] == "remote"

        if payload:
            job_posting = self.job_repo.update(
                job_posting, updated_by_id=recruiter.user_id, **payload
            )
        if "required_skills" in data or "preferred_skills" in data:
            self._sync_skills(job_posting, data, recruiter.user_id, replace=True)
        if "locations" in data:
            self._sync_locations(
                job_posting, data.get("locations"), recruiter.user_id, replace=True
            )

        self._audit(
            job_posting, "job.updated", recruiter.user_id, {"fields": sorted(payload)}
        )
        return job_posting

    @BaseService.atomic
    def duplicate_job(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        clone = self.job_repo.create(
            company=job_posting.company,
            posted_by=recruiter,
            title=f"{job_posting.title} (Copy)",
            slug=self._unique_slug(job_posting.company, job_posting.title),
            job_code="",
            category=job_posting.category,
            department=job_posting.department,
            description=job_posting.description,
            requirements=job_posting.requirements,
            roles_responsibilities=job_posting.roles_responsibilities,
            benefits=job_posting.benefits,
            education_requirement=job_posting.education_requirement,
            employment_type=job_posting.employment_type,
            work_mode=job_posting.work_mode,
            experience_min=job_posting.experience_min,
            experience_max=job_posting.experience_max,
            salary_min=job_posting.salary_min,
            salary_max=job_posting.salary_max,
            salary_currency=job_posting.salary_currency,
            salary_visibility=job_posting.salary_visibility,
            vacancies=job_posting.vacancies,
            joining_timeline=job_posting.joining_timeline,
            hiring_manager=job_posting.hiring_manager,
            country=job_posting.country,
            state=job_posting.state,
            city=job_posting.city,
            office_address=job_posting.office_address,
            location=job_posting.location,
            is_remote=job_posting.is_remote,
            visibility=job_posting.visibility,
            company_name_snapshot=job_posting.company.name,
            status=JobStatus.DRAFT,
            created_by_id=recruiter.user_id,
        )
        for link in job_posting.required_skills.filter(is_deleted=False).select_related(
            "skill"
        ):
            self.skill_repo.create(
                job_posting=clone,
                skill=link.skill,
                is_preferred=link.is_preferred,
                created_by_id=recruiter.user_id,
            )
        for loc in job_posting.locations.filter(is_deleted=False):
            self.location_repo.create(
                job_posting=clone,
                country=loc.country,
                state=loc.state,
                city=loc.city,
                office_address=loc.office_address,
                work_mode=loc.work_mode,
                is_primary=loc.is_primary,
                created_by_id=recruiter.user_id,
            )
        self._audit(
            clone,
            "job.duplicated",
            recruiter.user_id,
            {"source_id": str(job_posting.pk)},
        )
        return clone

    @BaseService.atomic
    def soft_delete(self, *, job_posting: JobPosting, recruiter) -> None:
        self._ensure_manages_job(job_posting, recruiter)
        job_posting.deleted_by_id = recruiter.user_id
        job_posting.save(update_fields=["deleted_by_id"])
        self.job_repo.soft_delete(job_posting)
        self._audit(job_posting, "job.deleted", recruiter.user_id, {})

    def _ensure_company_membership(self, company, recruiter) -> None:
        if not self.member_selector.is_member(recruiter, company.pk):
            raise PermissionDeniedException("You are not a member of this company.")

    def _guard_duplicate(self, company, title: str) -> None:
        """Prevent accidental duplicate submissions of the same active job."""
        active_statuses = (
            JobStatus.DRAFT,
            JobStatus.PENDING_APPROVAL,
            JobStatus.PUBLISHED,
            JobStatus.PAUSED,
        )
        if JobPosting.objects.filter(
            company=company, title__iexact=title.strip(), status__in=active_statuses
        ).exists():
            raise ConflictException(
                "An active job with this title already exists for this company."
            )

    def _unique_slug(self, company, title: str) -> str:
        base = slugify(title)[:340] or "job"
        slug = base
        while JobPosting.all_objects.filter(company=company, slug=slug).exists():
            suffix = f"-{uuid.uuid4().hex[:6]}"
            slug = f"{base[: 350 - len(suffix)]}{suffix}"
        return slug

    def _sync_skills(
        self, job_posting: JobPosting, data: dict, actor_id, *, replace: bool = False
    ) -> None:
        if replace and ("required_skills" in data or "preferred_skills" in data):
            self.skill_repo.filter_by(job_posting=job_posting).update(is_deleted=True)
        self._attach_skills(
            job_posting, data.get("required_skills") or [], actor_id, preferred=False
        )
        self._attach_skills(
            job_posting, data.get("preferred_skills") or [], actor_id, preferred=True
        )

    def _attach_skills(
        self, job_posting: JobPosting, names, actor_id, *, preferred: bool
    ) -> None:
        for raw in names:
            name = str(raw).strip()
            if not name:
                continue
            skill = self._resolve_skill(name, actor_id)
            self.skill_repo.model.all_objects.update_or_create(
                job_posting=job_posting,
                skill=skill,
                defaults={
                    "is_preferred": preferred,
                    "is_deleted": False,
                    "created_by_id": actor_id,
                },
            )

    @staticmethod
    def _resolve_skill(name: str, actor_id) -> Skill:
        # Match against all rows (including soft-deleted) to respect the unique
        # name constraint, restoring a soft-deleted skill if needed.
        skill = Skill.all_objects.filter(name__iexact=name).first()
        if skill is None:
            return Skill.objects.create(name=name, created_by_id=actor_id)
        if skill.is_deleted:
            skill.is_deleted = False
            skill.deleted_at = None
            skill.save(update_fields=["is_deleted", "deleted_at"])
        return skill

    def _sync_locations(
        self, job_posting: JobPosting, locations, actor_id, *, replace: bool = False
    ) -> None:
        if locations is None:
            return
        if replace:
            self.location_repo.filter_by(job_posting=job_posting).update(
                is_deleted=True
            )
        for item in locations:
            self.location_repo.create(
                job_posting=job_posting,
                country=item.get("country", ""),
                state=item.get("state", ""),
                city=item.get("city", ""),
                office_address=item.get("office_address", ""),
                work_mode=item.get("work_mode", "onsite"),
                is_primary=bool(item.get("is_primary", False)),
                created_by_id=actor_id,
            )
