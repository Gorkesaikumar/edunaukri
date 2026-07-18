from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.applications.selectors.application_selector import (
    FacultyApplicationSelector,
    JobApplicationSelector,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.core.permissions.base import IsCollegeUser, IsITDomainUser, IsProfessorUser
from apps.core.permissions.roles import IsJobSeeker, IsRecruiter


class CanViewJobApplication(BasePermission):
    message = "You cannot view this application."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        application_id = view.kwargs.get("application_id")
        if not application_id:
            return True
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return True
        try:
            ApplicationAuthorizationService().ensure_can_view_it_application(
                application, request.user
            )
            return True
        except Exception:
            return False


class CanManageJobApplicationStatus(BasePermission):
    message = "You cannot update this application."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        return IsRecruiter().has_permission(
            request, view
        ) or IsJobSeeker().has_permission(request, view)


class CanManageFacultyApplicationStatus(BasePermission):
    message = "You cannot update this application."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        return IsCollegeUser().has_permission(
            request, view
        ) or IsProfessorUser().has_permission(request, view)


class CanApplyToJob(BasePermission):
    message = "Only job seekers can apply to jobs."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        return IsITDomainUser().has_permission(
            request, view
        ) and IsJobSeeker().has_permission(request, view)


class CanViewFacultyApplication(BasePermission):
    message = "You cannot view this faculty application."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        application_id = view.kwargs.get("application_id")
        if not application_id:
            return True
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return True
        try:
            ApplicationAuthorizationService().ensure_can_view_faculty_application(
                application, request.user
            )
            return True
        except Exception:
            return False


class CanApplyToFacultyVacancy(BasePermission):
    message = "Only professors can apply to faculty vacancies."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        return IsProfessorUser().has_permission(request, view)
