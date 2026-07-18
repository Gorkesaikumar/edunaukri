"""Middleware — block cross-user UUID portal access with audit logging."""

from __future__ import annotations

import re

from django.http import HttpResponseForbidden, JsonResponse

from apps.accounts.models.it_user import ITUser
from apps.authentication.services.identity_service import IdentityService
from apps.authentication.services.route_authorization_service import (
    RouteAuthorizationService,
)
from apps.authentication.services.web_jwt_service import WebJWTService

_JOBSEEKER_SCOPED = re.compile(r"^/jobseeker/(?P<user_uuid>[0-9a-f-]{36})(?:/|$)", re.I)
_RECRUITER_SCOPED = re.compile(r"^/recruiter/(?P<user_uuid>[0-9a-f-]{36})(?:/|$)", re.I)
_PROFESSOR_SCOPED = re.compile(r"^/professor/(?P<user_uuid>[0-9a-f-]{36})(?:/|$)", re.I)
_COLLEGE_SCOPED = re.compile(r"^/college/(?P<user_uuid>[0-9a-f-]{36})(?:/|$)", re.I)


class UUIDRouteAuthorizationMiddleware:
    """Compare URL user_uuid segment with the authenticated user on every scoped request."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._route_auth = RouteAuthorizationService()

    def __call__(self, request):
        match = (
            _JOBSEEKER_SCOPED.match(request.path)
            or _RECRUITER_SCOPED.match(request.path)
            or _PROFESSOR_SCOPED.match(request.path)
            or _COLLEGE_SCOPED.match(request.path)
        )
        if match:
            user = self._resolve_user(request)
            if user is not None:
                from apps.accounts.models.admin_user import AdminUser
                if isinstance(user, AdminUser):
                    return self.get_response(request)

                url_uuid = match.group("user_uuid")
                portal = "jobseeker"
                if _RECRUITER_SCOPED.match(request.path):
                    portal = "recruiter"
                elif _PROFESSOR_SCOPED.match(request.path):
                    portal = "professor"
                elif _COLLEGE_SCOPED.match(request.path):
                    portal = "college"

                domain_allowed = False
                from apps.accounts.models.it_user import ITUser
                from apps.accounts.models.professor_user import ProfessorUser
                from apps.accounts.models.college_user import CollegeUser
                from apps.accounts.services.role_assignment_service import RoleAssignmentService
                from apps.accounts.constants.enums import ITUserRoleType

                if portal == "jobseeker" and isinstance(user, ITUser):
                    roles = RoleAssignmentService().get_it_roles(user)
                    domain_allowed = ITUserRoleType.JOB_SEEKER in roles
                elif portal == "recruiter" and isinstance(user, ITUser):
                    roles = RoleAssignmentService().get_it_roles(user)
                    domain_allowed = ITUserRoleType.RECRUITER in roles
                elif portal == "professor" and isinstance(user, ProfessorUser):
                    domain_allowed = True
                elif portal == "college" and isinstance(user, CollegeUser):
                    domain_allowed = True

                if not domain_allowed or not IdentityService.uuids_match(user.pk, url_uuid):
                    self._route_auth.record_unauthorized_access(
                        authenticated_user=user,
                        requested_uuid=url_uuid,
                        request=request,
                        portal=portal,
                    )
                    if (
                        "/api/" in request.path
                        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
                    ):
                        return JsonResponse(
                            {"success": False, "error": "Forbidden."}, status=403
                        )
                    return HttpResponseForbidden(
                        "Forbidden — you may not access this portal."
                    )
        return self.get_response(request)

    @staticmethod
    def _resolve_user(request):
        from apps.accounts.models.admin_user import AdminUser
        from apps.accounts.models.college_user import CollegeUser
        from apps.accounts.models.it_user import ITUser
        from apps.accounts.models.professor_user import ProfessorUser

        user = WebJWTService.get_valid_it_user(request)
        if user is not None:
            return user
        user = WebJWTService.get_valid_college_user(request)
        if user is not None:
            return user
        candidate = getattr(request, "user", None)
        if candidate and candidate.is_authenticated:
            if isinstance(candidate, (ITUser, CollegeUser, ProfessorUser, AdminUser)):
                return candidate
        return None
