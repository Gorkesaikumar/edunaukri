from django.db.models import Count

from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication
from apps.applications.selectors.application_selector import (
    CollegeApplicationSelector,
    FacultyApplicationSelector,
    ProfessorApplicationSelector,
)
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService


class FacultyApplicationStatisticsService(BaseService):
    """Aggregated faculty application statistics for professors, colleges, and admins."""

    def __init__(self):
        self.selector = FacultyApplicationSelector()
        self.college_selector = CollegeApplicationSelector()
        self.professor_selector = ProfessorApplicationSelector()

    def _summarize(self, queryset) -> dict:
        status_counts = dict(
            queryset.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_status = {
            choice.value: status_counts.get(choice.value, 0)
            for choice in FacultyApplicationStatus
        }
        terminal = (
            FacultyApplicationStatus.JOINED,
            FacultyApplicationStatus.REJECTED,
            FacultyApplicationStatus.WITHDRAWN,
            FacultyApplicationStatus.EXPIRED,
            FacultyApplicationStatus.OFFER_DECLINED,
        )
        return {
            "total_applications": queryset.count(),
            "applications_by_status": by_status,
            "active_applications": queryset.exclude(status__in=terminal).count(),
        }

    def professor_dashboard(self, professor) -> dict:
        return self._summarize(self.professor_selector.for_professor(professor))

    def college_dashboard(self, college_user) -> dict:
        return self._summarize(self.college_selector.for_college_user(college_user))

    def institution_dashboard(self, *, college_id, college_user) -> dict:
        if (
            not CollegeMemberSelector()
            .for_user(college_user)
            .filter(college_id=college_id)
            .exists()
        ):
            raise PermissionDeniedException("You are not a member of this institution.")
        return self._summarize(self.selector.for_college(college_id))

    def platform_dashboard(self) -> dict:
        return self._summarize(self.selector.filter_by())

    def application_statistics(self, application: FacultyApplication) -> dict:
        return {
            "application_id": str(application.pk),
            "status": application.status,
            "applied_at": application.applied_at,
            "status_changed_at": application.status_changed_at,
            "joined_at": application.joined_at,
            "vacancy_id": str(application.vacancy_id),
            "college_id": str(application.college_id)
            if application.college_id
            else None,
        }
