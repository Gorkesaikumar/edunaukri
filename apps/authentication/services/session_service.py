import logging

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.db import transaction

from apps.authentication.services.login_service import LoginService
from apps.core.services.base import BaseService

logger = logging.getLogger(__name__)

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
        from django.contrib.auth import authenticate
        from django.core.exceptions import ValidationError
        
        user = authenticate(request, username=email, password=password, domain=domain)
        
        if user is None:
            if hasattr(request, "auth_validation_error"):
                raise request.auth_validation_error
            raise ValidationError("Invalid credentials.")
            
        django_login(request, user)
        request.session.cycle_key()
        request.session["_auth_domain"] = domain
        return user

    @transaction.atomic
    def login_user(self, request, *, domain: str, user):
        """Establish a Django session for an already-authenticated user (e.g. OAuth)."""
        if user is None:
            raise ValueError(
                f"SessionService.login_user() received user=None for domain='{domain}'. "
                "The OAuth account linking service failed to resolve or create a user."
            )
        backend = BACKEND_MAP.get(domain)
        if not backend:
            raise ValueError(
                f"Unsupported domain for session login: '{domain}'. "
                f"Supported domains: {list(BACKEND_MAP.keys())}"
            )
        logger.info(
            "SessionService.login_user: domain=%s, user_pk=%s, user_email=%s, backend=%s",
            domain, user.pk, getattr(user, 'email', '?'), backend,
        )
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
