"""Object-level permissions for the Faculty Vacancy Management module."""

from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector


class CanManageVacancy(BasePermission):
    """Allow college users that belong to the vacancy's institution (admins bypass).

    Resolves ``vacancy_id`` from the view kwargs; when absent (list/create routes)
    it defers to the service layer for institution-membership checks.
    """

    message = "You do not manage this vacancy."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        vacancy_id = view.kwargs.get("vacancy_id")
        if not vacancy_id:
            return True
        vacancy = FacultyVacancySelector().get_or_none(vacancy_id)
        if not vacancy:
            return True  # let the view return 404
        return CollegeMemberSelector().is_member(request.user, vacancy.college_id)
