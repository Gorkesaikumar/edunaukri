from apps.core.selectors.read import ReadSelector
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting
from apps.jobs.selectors.job_selector import CompanyJobSelector, RecruiterJobSelector


class JobDashboardSelector(ReadSelector):
    model = JobPosting

    def _summarize(self, queryset) -> dict:
        by_status = {
            choice.value: queryset.filter(status=choice.value).count()
            for choice in JobStatus
        }
        return {
            "total_jobs": queryset.count(),
            "published_jobs": by_status.get(JobStatus.PUBLISHED, 0),
            "draft_jobs": by_status.get(JobStatus.DRAFT, 0),
            "featured_jobs": queryset.filter(
                status=JobStatus.PUBLISHED, is_featured=True
            ).count(),
            "urgent_jobs": queryset.filter(
                status=JobStatus.PUBLISHED, is_urgent=True
            ).count(),
            "jobs_by_status": by_status,
        }

    def recruiter_summary(self, recruiter) -> dict:
        return self._summarize(RecruiterJobSelector().for_recruiter(recruiter))

    def company_summary(self, company_id) -> dict:
        return self._summarize(CompanyJobSelector().for_company(company_id))

    def platform_summary(self) -> dict:
        return self._summarize(self.filter_by())

    def job_statistics(self, job_posting: JobPosting) -> dict:
        return {
            "job_id": str(job_posting.pk),
            "title": job_posting.title,
            "status": job_posting.status,
            "application_count": job_posting.application_count,
            "view_count": job_posting.view_count,
            "vacancies": job_posting.vacancies,
            "is_featured": job_posting.is_featured,
            "is_urgent": job_posting.is_urgent,
            "published_at": job_posting.published_at,
            "expires_at": job_posting.expires_at,
        }
