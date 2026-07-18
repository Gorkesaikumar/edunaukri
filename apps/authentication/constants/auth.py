"""Centralized authentication constants."""

from django.conf import settings

MAX_FAILED_LOGIN_ATTEMPTS = getattr(settings, "AUTH_MAX_FAILED_LOGIN_ATTEMPTS", 5)
LOCKOUT_MINUTES = getattr(settings, "AUTH_LOCKOUT_MINUTES", 30)
REQUIRE_EMAIL_VERIFICATION = getattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", False)

DOMAIN_USER_MAP = {
    "admin": "apps.accounts.models.admin_user.AdminUser",
    "it": "apps.accounts.models.it_user.ITUser",
    "professor": "apps.accounts.models.professor_user.ProfessorUser",
    "college": "apps.accounts.models.college_user.CollegeUser",
    "faculty": "apps.accounts.models.faculty_user.FacultyUser",
}
