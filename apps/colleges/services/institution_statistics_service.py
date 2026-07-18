from apps.colleges.models import College
from apps.colleges.selectors.college_selector import (
    CollegeDepartmentSelector,
    CollegeMemberSelector,
    InstitutionCampusSelector,
    InstitutionDashboardSelector,
    InstitutionDocumentSelector,
)
from apps.core.services.base import BaseService


class InstitutionStatisticsService(BaseService):
    """Aggregated, read-only statistics for institutions and college dashboards."""

    def __init__(self):
        self.dashboard_selector = InstitutionDashboardSelector()
        self.member_selector = CollegeMemberSelector()
        self.department_selector = CollegeDepartmentSelector()
        self.campus_selector = InstitutionCampusSelector()
        self.document_selector = InstitutionDocumentSelector()

    def college_dashboard(self, college_user) -> dict:
        return self.dashboard_selector.summary_for_user(college_user)

    def platform_dashboard(self) -> dict:
        return self.dashboard_selector.platform_summary()

    def institution_statistics(self, institution: College) -> dict:
        verification_status = getattr(
            institution, "verification_status", None
        ) or getattr(institution, "profile_status", "")
        return {
            "institution_id": str(institution.pk),
            "name": institution.name,
            "verification_status": verification_status,
            "is_active": institution.is_active,
            "member_count": self.member_selector.for_college(institution.pk).count(),
            "department_count": self.department_selector.for_college(
                institution.pk
            ).count(),
            "campus_count": self.campus_selector.for_college(institution.pk).count(),
            "document_count": self.document_selector.for_college(
                institution.pk
            ).count(),
            "vacancy_count": self._vacancy_count(institution),
        }

    def _vacancy_count(self, institution: College) -> int:
        try:
            from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector

            return FacultyVacancySelector().filter_by(college_id=institution.pk).count()
        except Exception:  # noqa: BLE001 - faculty module optional for statistics
            return 0
