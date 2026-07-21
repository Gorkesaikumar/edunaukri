"""Recruiter Settings & Security Center API."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.services.connected_accounts_service import (
    ConnectedAccountsService,
)
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import (
    DomainException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.recruiter_account_settings_service import (
    RecruiterAccountSettingsService,
)
from apps.it_recruitment.services.recruiter_password_service import (
    RecruiterPasswordService,
)
from apps.it_recruitment.views.recruiter_api_base import RecruiterScopedAPIView


def _get_profile(user) -> RecruiterProfile | None:
    return (
        RecruiterProfile.objects.filter(user=user, is_deleted=False)
        .select_related("user")
        .first()
    )


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _error_response(exc):
    if isinstance(exc, ResourceNotFoundException):
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
    if isinstance(exc, ValidationException):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    if isinstance(exc, DomainException):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _meta(request) -> dict:
    return {
        "ip_address": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
    }


def _authorized(request) -> RecruiterProfile | None:
    if not RoleAssignmentService().user_has_it_role(
        request.user, ITUserRoleType.RECRUITER
    ):
        return None
    return _get_profile(request.user)


def _parse_json(request) -> dict:
    return json.loads(request.body.decode("utf-8") or "{}")


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsAccountAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def patch(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = RecruiterAccountSettingsService().update_account_info(
                profile, data, actor_id=request.user.pk, request_meta=_meta(request)
            )
            return JsonResponse(
                {
                    "success": True,
                    "data": result,
                    "message": "Account information updated.",
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsPasswordAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = RecruiterPasswordService().change_password(
                profile,
                current_password=data.get("current_password", ""),
                new_password=data.get("new_password", ""),
                confirm_password=data.get("confirm_password", ""),
                request=request,
            )
            revoked = result.get("sessions_revoked", 0)
            message = "Password changed successfully."
            if revoked:
                message += f" {revoked} other session(s) were signed out."
            return JsonResponse({"success": True, "message": message, "data": result})
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsNotificationsAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def patch(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = RecruiterAccountSettingsService().update_notifications(
                profile, data
            )
            return JsonResponse(
                {
                    "success": True,
                    "data": result,
                    "message": "Notification preferences saved.",
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsSessionsAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def get(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        svc = SessionManagementService()
        current = svc.current_session_key_from_request(request)
        items = svc.list_sessions(
            domain=DomainType.IT, user_id=profile.user_id, current_session_key=current
        )
        return JsonResponse({"success": True, "data": {"items": items}})


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsSessionDetailAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["delete"]

    def delete(self, request, session_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            svc = SessionManagementService()
            current = svc.current_session_key_from_request(request)
            svc.revoke_session(
                domain=DomainType.IT,
                user_id=profile.user_id,
                session_id=session_id,
                current_session_key=current,
            )
            return JsonResponse({"success": True, "message": "Session signed out."})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsRevokeSessionsAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        svc = SessionManagementService()
        current = svc.current_session_key_from_request(request)
        count = svc.revoke_other_sessions(
            domain=DomainType.IT,
            user_id=profile.user_id,
            current_session_key=current,
            request_meta=_meta(request),
        )
        return JsonResponse(
            {"success": True, "message": f"Signed out of {count} other device(s)."}
        )


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsConnectedAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def get(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.authentication.services.portal_url_service import PortalURLService

        items = ConnectedAccountsService().list_for_user(
            domain=DomainType.IT,
            user_id=profile.user_id,
            settings_return_url=PortalURLService.recruiter(
                profile.user, "recruiter_settings"
            ),
        )
        return JsonResponse({"success": True, "data": {"items": items}})

    def delete(self, request, provider):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            result = ConnectedAccountsService().disconnect(
                domain=DomainType.IT,
                user_id=profile.user_id,
                provider=provider,
                request_meta=_meta(request),
            )
            return JsonResponse(
                {"success": True, "data": result, "message": "Account disconnected."}
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsDeleteAccountAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            RecruiterAccountSettingsService().delete_account(
                profile,
                password=data.get("password", ""),
                actor_id=request.user.pk,
                request_meta=_meta(request),
            )
            jwt_service = WebJWTService()
            refresh = request.COOKIES.get(jwt_service.refresh_cookie)
            jwt_service.logout(refresh_token=refresh, request_meta=_meta(request))
            SessionService().logout(request)
            response = JsonResponse(
                {
                    "success": True,
                    "message": "Your account has been deactivated.",
                    "redirect_url": "/it/login/recruiter/",
                }
            )
            jwt_service.clear_tokens(response)
            return response
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterSettingsAuditAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def get(self, request, *args, **kwargs):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        events = SecurityAuditService().list_activity_for_user(
            domain=DomainType.IT, user_id=profile.user_id, limit=25
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "items": [SecurityAuditService.serialize_event(e) for e in events]
                },
            }
        )
