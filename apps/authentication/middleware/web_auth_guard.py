"""Redirect authenticated users away from guest auth routes; prevent sensitive page caching."""

from django.http import HttpResponseRedirect

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.authentication.constants.web_auth import (
    FACULTY_GUEST_ROUTE_PREFIXES,
    IT_GUEST_ROUTE_PREFIXES,
    WEB_SENSITIVE_ROUTE_PREFIXES,
)
from apps.authentication.services.web_jwt_service import WebJWTService


class WebAuthGuardMiddleware:
    """
    • Blocks authenticated users from login/signup pages (server-side back-button guard).
    • Applies Cache-Control: no-store on auth and dashboard routes.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._jwt = WebJWTService()

    def __call__(self, request):
        if request.method == "GET":
            user = self._guest_route_user(request)
            if user is not None:
                return HttpResponseRedirect(WebJWTService.resolve_dashboard_url(user))

        response = self.get_response(request)

        if self._is_sensitive_route(request.path):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response

    def _guest_route_user(self, request):
        path = request.path
        if self._is_it_guest_route(path):
            user = WebJWTService.get_valid_it_user(request)
            if user is not None and isinstance(user, ITUser):
                return user
            return None
        if self._is_faculty_guest_route(path):
            user = WebJWTService.get_valid_web_user(request)
            if user is not None and isinstance(user, (ProfessorUser, CollegeUser)):
                return user
        return None

    @staticmethod
    def _is_it_guest_route(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in IT_GUEST_ROUTE_PREFIXES)

    @staticmethod
    def _is_faculty_guest_route(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in FACULTY_GUEST_ROUTE_PREFIXES)

    @staticmethod
    def _is_sensitive_route(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in WEB_SENSITIVE_ROUTE_PREFIXES)
