"""Institution settings JSON API."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.college_user import CollegeUser
from apps.academic_recruitment.services.college_account_settings_service import (
    CollegeAccountSettingsService,
)
from apps.academic_recruitment.services.college_password_service import (
    CollegePasswordService,
)
from apps.academic_recruitment.views.college_api_base import CollegeScopedAPIView
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.authentication.services.connected_accounts_service import (
    ConnectedAccountsService,
)
from apps.core.exceptions.domain_exceptions import (
    DomainException,
    ResourceNotFoundException,
    ValidationException,
)

COLLEGE_DOMAIN = "college"


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _parse_json(request) -> dict:
    return json.loads(request.body.decode("utf-8") or "{}")


def _meta(request) -> dict:
    return {
        "ip_address": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
    }


def _college_user(user) -> CollegeUser | None:
    return user if isinstance(user, CollegeUser) else None


def _error_response(exc):
    if isinstance(exc, ResourceNotFoundException):
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
    if isinstance(exc, (ValidationException, DomainException)):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": False, "error": str(exc)}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class CollegeSettingsAccountAPIView(CollegeScopedAPIView):
    def patch(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = CollegeAccountSettingsService().update_account_info(
                user, data, request_meta=_meta(request)
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
class CollegeSettingsPasswordAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = CollegePasswordService().change_password(
                user,
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
class CollegeSettingsNotificationsAPIView(CollegeScopedAPIView):
    def patch(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = CollegeAccountSettingsService().update_notifications(user, data)
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
class CollegeSettingsPrivacyAPIView(CollegeScopedAPIView):
    def patch(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        try:
            data = _parse_json(request)
            result = CollegeAccountSettingsService().update_privacy(user, data)
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


class CollegeSettingsSessionsAPIView(CollegeScopedAPIView):
    def get(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        svc = SessionManagementService()
        current = svc.current_session_key_from_request(request)
        items = svc.list_sessions(
            domain=COLLEGE_DOMAIN, user_id=user.pk, current_session_key=current
        )
        return JsonResponse({"success": True, "data": {"items": items}})


@method_decorator(csrf_protect, name="dispatch")
class CollegeSettingsSessionDetailAPIView(CollegeScopedAPIView):
    http_method_names = ["delete"]

    def delete(self, request, session_id, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        try:
            svc = SessionManagementService()
            current = svc.current_session_key_from_request(request)
            svc.revoke_session(
                domain=COLLEGE_DOMAIN,
                user_id=user.pk,
                session_id=session_id,
                current_session_key=current,
            )
            return JsonResponse({"success": True, "message": "Session signed out."})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class CollegeSettingsRevokeSessionsAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        svc = SessionManagementService()
        current = svc.current_session_key_from_request(request)
        count = svc.revoke_other_sessions(
            domain=COLLEGE_DOMAIN,
            user_id=user.pk,
            current_session_key=current,
            request_meta=_meta(request),
        )
        return JsonResponse(
            {"success": True, "message": f"Signed out of {count} other device(s)."}
        )


@method_decorator(csrf_protect, name="dispatch")
class CollegeSettingsDeleteAccountAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        try:
            data = _parse_json(request)
            CollegeAccountSettingsService().delete_account(
                user,
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
                    "redirect_url": "/faculty/login/institution/",
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


class CollegeSettingsAuditAPIView(CollegeScopedAPIView):
    def get(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        events = SecurityAuditService().list_activity_for_user(
            domain=COLLEGE_DOMAIN, user_id=user.pk, limit=25
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
class CollegeSettingsConnectedAPIView(CollegeScopedAPIView):
    http_method_names = ["get", "delete"]

    def get(self, request, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        data = ConnectedAccountsService().list_for_user(
            domain=COLLEGE_DOMAIN,
            user_id=user.pk,
        )
        return JsonResponse({"success": True, "data": {"items": data}})

    def delete(self, request, provider=None, **kwargs):
        user = _college_user(request.user)
        if not user:
            return _forbidden()
        if not provider:
            return JsonResponse(
                {"success": False, "error": "Provider is required."}, status=400
            )
        try:
            result = ConnectedAccountsService().disconnect(
                domain=COLLEGE_DOMAIN,
                user_id=user.pk,
                provider=provider,
                request_meta=_meta(request),
            )
            return JsonResponse(
                {
                    "success": True,
                    "data": result,
                    "message": "Connected account removed.",
                }
            )
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)
