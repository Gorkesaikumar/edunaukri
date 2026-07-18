from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_dashboard import VacancyDashboardSelector


class FacultyStatisticsService(BaseService):
    """Aggregated, read-only vacancy statistics for college users and admins."""

    def __init__(self):
        self.dashboard = VacancyDashboardSelector()
        self.member_selector = CollegeMemberSelector()

    def college_user_dashboard(self, college_user) -> dict:
        return self.dashboard.college_user_summary(college_user)

    def college_dashboard(self, *, college_id, college_user) -> dict:
        if not self.member_selector.is_member(college_user, college_id):
            raise PermissionDeniedException("You are not a member of this institution.")
        return self.dashboard.college_summary(college_id)

    def platform_dashboard(self) -> dict:
        return self.dashboard.platform_summary()

    def vacancy_statistics(self, *, vacancy: FacultyVacancy, college_user) -> dict:
        if not self.member_selector.is_member(college_user, vacancy.college_id):
            raise PermissionDeniedException("You do not manage this vacancy.")
        return self.dashboard.vacancy_statistics(vacancy)
