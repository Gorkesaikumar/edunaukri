from apps.admin_panel.services.admin_audit import record_admin_action
from apps.core.services.base import BaseService
from apps.faculty.services.vacancy_lifecycle_service import FacultyLifecycleService
from apps.faculty.services.vacancy_publication_service import FacultyPublicationService
from apps.faculty.services.vacancy_statistics_service import FacultyStatisticsService
from apps.faculty.services.vacancy_visibility_service import FacultyVisibilityService


class AdminFacultyService(BaseService):
    def __init__(self):
        self.publication = FacultyPublicationService()
        self.lifecycle = FacultyLifecycleService()
        self.visibility = FacultyVisibilityService()
        self.statistics = FacultyStatisticsService()

    def platform_statistics(self) -> dict:
        return self.statistics.platform_dashboard()

    @BaseService.atomic
    def approve(self, vacancy, *, admin_id, remarks: str = ""):
        vacancy = self.publication.admin_approve(
            vacancy=vacancy, admin_id=admin_id, remarks=remarks
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.vacancy.approved",
            entity_type="faculty_vacancy",
            entity_id=vacancy.pk,
        )
        return vacancy

    @BaseService.atomic
    def reject(self, vacancy, *, admin_id, remarks: str = ""):
        vacancy = self.publication.admin_reject(
            vacancy=vacancy, admin_id=admin_id, remarks=remarks
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.vacancy.rejected",
            entity_type="faculty_vacancy",
            entity_id=vacancy.pk,
        )
        return vacancy

    @BaseService.atomic
    def close(self, vacancy, *, admin_id):
        vacancy = self.lifecycle.admin_close(vacancy=vacancy, admin_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.vacancy.closed",
            entity_type="faculty_vacancy",
            entity_id=vacancy.pk,
        )
        return vacancy

    @BaseService.atomic
    def archive(self, vacancy, *, admin_id):
        vacancy = self.lifecycle.admin_archive(vacancy=vacancy, admin_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.vacancy.archived",
            entity_type="faculty_vacancy",
            entity_id=vacancy.pk,
        )
        return vacancy

    @BaseService.atomic
    def set_featured(self, vacancy, *, admin_id, value: bool):
        vacancy = self.visibility.admin_set_featured(
            vacancy=vacancy, admin_id=admin_id, value=value
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.vacancy.featured",
            entity_type="faculty_vacancy",
            entity_id=vacancy.pk,
            payload={"is_featured": value},
        )
        return vacancy
