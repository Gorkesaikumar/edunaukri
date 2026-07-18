from apps.admin_panel.services.admin_audit import record_admin_action
from apps.admin_panel.services.admin_export_service import AdminExportService
from apps.applications.selectors.application_selector import (
    FacultyApplicationSelector,
    JobApplicationSelector,
)
from apps.applications.selectors.status_history_selector import (
    FacultyApplicationStatusHistorySelector,
    JobApplicationStatusHistorySelector,
)
from apps.applications.services.application_service import JobApplicationService
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.core.services.base import BaseService


class AdminApplicationService(BaseService):
    def __init__(self):
        self.job_selector = JobApplicationSelector()
        self.faculty_selector = FacultyApplicationSelector()
        self.job_service = JobApplicationService()
        self.faculty_service = FacultyApplicationService()
        self.export = AdminExportService()

    def update_job_status(
        self, application, *, status, notes, actor, rejection_reason=""
    ):
        application = self.job_service.update_status_for_actor(
            application,
            status,
            notes,
            actor=actor,
            rejection_reason=rejection_reason,
        )
        return application

    def update_faculty_status(
        self, application, *, status, notes, actor, rejection_reason=""
    ):
        application = self.faculty_service.update_status_for_actor(
            application,
            status,
            notes,
            actor=actor,
            rejection_reason=rejection_reason,
        )
        return application

    def job_history(self, application):
        return JobApplicationStatusHistorySelector().for_application(application)

    def faculty_history(self, application):
        return FacultyApplicationStatusHistorySelector().for_application(application)

    def export_job_applications(self, **filters):
        apps = self.job_selector.admin_list(**filters)
        rows = [
            {
                "id": str(app.pk),
                "status": app.status,
                "job_title": app.job_title_snapshot,
                "company": app.company_name_snapshot,
                "applicant": app.applicant_name_snapshot,
                "applied_at": app.applied_at.isoformat() if app.applied_at else "",
            }
            for app in apps[:5000]
        ]
        return self.export.to_csv(rows), "text/csv", "job_applications.csv"

    def export_faculty_applications(self, **filters):
        apps = self.faculty_selector.admin_list(**filters)
        rows = [
            {
                "id": str(app.pk),
                "status": app.status,
                "vacancy_title": app.vacancy_title_snapshot,
                "college": app.college_name_snapshot,
                "applicant": app.applicant_name_snapshot,
                "applied_at": app.applied_at.isoformat() if app.applied_at else "",
            }
            for app in apps[:5000]
        ]
        return self.export.to_csv(rows), "text/csv", "faculty_applications.csv"

    def record_status_override(
        self, *, admin_id, domain: str, application_id, status: str
    ):
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.application.status_override",
            entity_type=f"{domain}_application",
            entity_id=application_id,
            payload={"status": status},
        )
