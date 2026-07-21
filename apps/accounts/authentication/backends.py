from django.core.exceptions import ValidationError
from django.conf import settings

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.faculty_user import FacultyUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.authentication.services.login_service import LoginService


def _is_admin_site_request(request) -> bool:
    if request is None:
        return False
    admin_url = (getattr(settings, "ADMIN_URL", "admin/") or "admin/").strip("/")
    path = (request.path or "").strip("/")
    return path == admin_url or path.startswith(f"{admin_url}/")


class DomainAuthBackend:
    """Authenticate domain users through the centralized LoginService."""

    domain = None
    user_model = None

    def authenticate(self, request, username=None, password=None, **kwargs):
        if _is_admin_site_request(request) and self.user_model is not AdminUser:
            return None

        email = kwargs.get("email") or username
        if not email or not password or not self.domain:
            return None

        meta = {}
        if request is not None:
            meta = {
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
            }

        try:
            return LoginService().authenticate(
                domain=self.domain,
                email=email,
                password=password,
                request_meta=meta,
            )
        except ValidationError as exc:
            if request is not None:
                request.auth_validation_error = exc
            return None

    def get_user(self, user_id):
        if self.user_model is None:
            return None
        return self.user_model.objects.filter(
            pk=user_id, is_deleted=False, is_active=True
        ).first()


class AdminUserAuthBackend(DomainAuthBackend):
    domain = "admin"
    user_model = AdminUser


class ITUserAuthBackend(DomainAuthBackend):
    domain = "it"
    user_model = ITUser


class ProfessorUserAuthBackend(DomainAuthBackend):
    domain = "professor"
    user_model = ProfessorUser


class CollegeUserAuthBackend(DomainAuthBackend):
    domain = "college"
    user_model = CollegeUser


class FacultyUserAuthBackend(DomainAuthBackend):
    """Legacy faculty auth backend — prefer professor/college backends."""

    domain = "faculty"
    user_model = FacultyUser
