from apps.admin_panel.services.admin_audit import record_admin_action
from apps.core.services.base import BaseService
from apps.jobs.services.job_lifecycle_service import JobLifecycleService
from apps.jobs.services.job_publication_service import JobPublicationService
from apps.jobs.services.job_statistics_service import JobStatisticsService
from apps.jobs.services.job_visibility_service import JobVisibilityService


class AdminJobService(BaseService):
    def __init__(self):
        self.publication = JobPublicationService()
        self.lifecycle = JobLifecycleService()
        self.visibility = JobVisibilityService()
        self.statistics = JobStatisticsService()

    def platform_statistics(self) -> dict:
        return self.statistics.platform_dashboard()

    @BaseService.atomic
    def approve(self, job, *, admin_id, remarks: str = ""):
        job = self.publication.admin_approve(
            job_posting=job, admin_id=admin_id, remarks=remarks
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.job.approved",
            entity_type="it_job_posting",
            entity_id=job.pk,
        )
        return job

    @BaseService.atomic
    def reject(self, job, *, admin_id, remarks: str = ""):
        job = self.publication.admin_reject(
            job_posting=job, admin_id=admin_id, remarks=remarks
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.job.rejected",
            entity_type="it_job_posting",
            entity_id=job.pk,
        )
        return job

    @BaseService.atomic
    def close(self, job, *, admin_id):
        job = self.lifecycle.admin_close(job_posting=job, admin_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.job.closed",
            entity_type="it_job_posting",
            entity_id=job.pk,
        )
        return job

    @BaseService.atomic
    def archive(self, job, *, admin_id):
        job = self.lifecycle.admin_archive(job_posting=job, admin_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.job.archived",
            entity_type="it_job_posting",
            entity_id=job.pk,
        )
        return job

    @BaseService.atomic
    def set_featured(self, job, *, admin_id, value: bool):
        job = self.visibility.admin_set_featured(
            job_posting=job, admin_id=admin_id, value=value
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.job.featured",
            entity_type="it_job_posting",
            entity_id=job.pk,
            payload={"is_featured": value},
        )
        return job
