from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.db import transaction

from apps.authentication.services.login_service import LoginService
from apps.core.services.base import BaseService


BACKEND_MAP = {
    "it": "apps.accounts.authentication.backends.ITUserAuthBackend",
    "professor": "apps.accounts.authentication.backends.ProfessorUserAuthBackend",
    "college": "apps.accounts.authentication.backends.CollegeUserAuthBackend",
    "faculty": "apps.accounts.authentication.backends.FacultyUserAuthBackend",
    "admin": "django.contrib.auth.backends.ModelBackend",
}


class SessionService(BaseService):
    @transaction.atomic
    def login(self, request, *, domain: str, email: str, password: str):
        user = LoginService().authenticate(
            domain=domain,
            email=email,
            password=password,
            request_meta=self._meta(request),
        )
        backend = BACKEND_MAP.get(domain)
        if not backend:
            raise ValueError("Unsupported domain for session login.")
        user.backend = backend
        django_login(request, user)
        request.session.cycle_key()
        request.session["_auth_domain"] = domain
        return user

    @transaction.atomic
    def login_user(self, request, *, domain: str, user):
        """Establish a Django session for an already-authenticated user (e.g. OAuth)."""
        backend = BACKEND_MAP.get(domain)
        if not backend:
            raise ValueError("Unsupported domain for session login.")
        user.backend = backend
        django_login(request, user)
        request.session.cycle_key()
        request.session["_auth_domain"] = domain
        return user

    def logout(self, request) -> None:
        if hasattr(request, "session"):
            request.session.pop("_auth_domain", None)
        django_logout(request)

    @staticmethod
    def _meta(request):
        if not request:
            return {}
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
