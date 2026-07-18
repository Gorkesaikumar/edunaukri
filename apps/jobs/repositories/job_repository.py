from django.db.models import F

from apps.core.repositories.crud import CRUDRepository, ReadRepository
from apps.jobs.models import JobLocation, JobPosting, JobPostingSkill


class JobReadRepository(ReadRepository):
    model = JobPosting


class JobPostingRepository(CRUDRepository):
    model = JobPosting
    search_fields = ("title", "location", "company_name_snapshot", "job_code")

    def increment_application_count(self, job_posting: JobPosting) -> None:
        self.filter_by(pk=job_posting.pk).update(
            application_count=F("application_count") + 1
        )

    def increment_view_count(self, job_posting: JobPosting) -> None:
        self.filter_by(pk=job_posting.pk).update(view_count=F("view_count") + 1)


# Canonical alias exposed by the Job Management module.
JobRepository = JobPostingRepository


class JobLocationRepository(CRUDRepository):
    model = JobLocation


class JobPostingSkillRepository(CRUDRepository):
    model = JobPostingSkill
