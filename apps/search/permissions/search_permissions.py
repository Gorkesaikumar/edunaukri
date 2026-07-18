from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser


class IsAdminOrCollegeUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return isinstance(user, (AdminUser, CollegeUser)) and user.is_active
