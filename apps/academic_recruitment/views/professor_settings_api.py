"""Professor settings JSON API."""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_account_settings_service import (
    ProfessorAccountSettingsService,
)
from apps.academic_recruitment.services.professor_password_service import (
    ProfessorPasswordService,
)
from apps.academic_recruitment.services.professor_privacy_settings_service import (
    ProfessorPrivacySettingsService,
)
from apps.authentication.services.connected_accounts_service import (
    ConnectedAccountsService,
)
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.exceptions.domain_exceptions import (
    DomainException,
    ResourceNotFoundException,
    ValidationException,
)

PROFESSOR_DOMAIN = "professor"


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _parse_json(request) -> dict:
    return json.loads(request.body.decode("utf-8") or "{}")


def _meta(request) -> dict:
    return {
        "ip_address": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
    }


def _profile(user) -> ProfessorProfile | None:
    if not isinstance(user, ProfessorUser):
        return None
    return (
        ProfessorProfile.objects.filter(user=user, is_deleted=False)
        .select_related("user")
        .first()
    )


def _error_response(exc):
    if isinstance(exc, ResourceNotFoundException):
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
    if isinstance(exc, (ValidationException, DomainException)):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": False, "error": str(exc)}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorSettingsAccountAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def patch(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = ProfessorAccountSettingsService().update_account_info(
                profile, data, request_meta=_meta(request)
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
class ProfessorSettingsPasswordAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = ProfessorPasswordService().change_password(
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
class ProfessorSettingsNotificationsAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def patch(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = ProfessorAccountSettingsService().update_notifications(
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
class ProfessorSettingsPrivacyAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def patch(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = ProfessorPrivacySettingsService().update(
                profile, data, request_meta=_meta(request)
            )
            return JsonResponse(
                {
                    "success": True,
                    "data": result["data"],
                    "message": result["message"],
                    "changed_fields": result.get("changed_fields", []),
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


class ProfessorSettingsSessionsAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        svc = SessionManagementService()
        current = svc.current_session_key_from_request(request)
        items = svc.list_sessions(
            domain=PROFESSOR_DOMAIN,
            user_id=profile.user_id,
            current_session_key=current,
        )
        return JsonResponse({"success": True, "data": {"items": items}})


@method_decorator(csrf_protect, name="dispatch")
class ProfessorSettingsSessionDetailAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["delete"]

    def delete(self, request, session_id, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            svc = SessionManagementService()
            current = svc.current_session_key_from_request(request)
            svc.revoke_session(
                domain=PROFESSOR_DOMAIN,
                user_id=profile.user_id,
                session_id=session_id,
                current_session_key=current,
            )
            return JsonResponse({"success": True, "message": "Session signed out."})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorSettingsRevokeSessionsAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        svc = SessionManagementService()
        current = svc.current_session_key_from_request(request)
        count = svc.revoke_other_sessions(
            domain=PROFESSOR_DOMAIN,
            user_id=profile.user_id,
            current_session_key=current,
            request_meta=_meta(request),
        )
        return JsonResponse(
            {"success": True, "message": f"Signed out of {count} other device(s)."}
        )


@method_decorator(csrf_protect, name="dispatch")
class ProfessorSettingsDeleteAccountAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            ProfessorAccountSettingsService().delete_account(
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
                    "redirect_url": "/faculty/login/professor/",
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


class ProfessorSettingsAuditAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        events = SecurityAuditService().list_activity_for_user(
            domain=PROFESSOR_DOMAIN, user_id=profile.user_id, limit=25
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "items": [SecurityAuditService.serialize_event(e) for e in events]
                },
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class ProfessorSettingsConnectedAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def delete(self, request, provider, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return _forbidden()
        try:
            result = ConnectedAccountsService().disconnect(
                domain=PROFESSOR_DOMAIN,
                user_id=profile.user_id,
                provider=provider,
                request_meta=_meta(request),
            )
            return JsonResponse(
                {"success": True, "data": result, "message": "Account disconnected."}
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)
