"""Web authentication views — logout, session probe, JWT refresh."""

import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService

logger = logging.getLogger(__name__)


class WebSessionStatusView(View):
    """Returns whether the current browser session is authenticated (for bfcache/back-button guard)."""

    http_method_names = ["get"]

    def get(self, request):
        user = WebJWTService.get_valid_web_user(request)
        if user is not None:
            return JsonResponse(
                {
                    "authenticated": True,
                    "redirect_url": WebJWTService.resolve_dashboard_url(user),
                }
            )
        return JsonResponse({"authenticated": False})


class WebTokenRefreshView(View):
    """Silently refresh the access token using the HttpOnly refresh cookie."""

    http_method_names = ["post"]

    def post(self, request):
        jwt_service = WebJWTService()
        refresh = request.COOKIES.get(jwt_service.refresh_cookie)
        meta = {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
        if not refresh:
            return JsonResponse(
                {"success": False, "error": "No refresh token."}, status=401
            )

        try:
            access, rotated = jwt_service.refresh_access_token(
                refresh_token=refresh, request_meta=meta
            )
        except ValueError:
            response = JsonResponse(
                {"success": False, "error": "Session expired."}, status=401
            )
            jwt_service.clear_tokens(response)
            SessionService().logout(request)
            return response

        secure_flag = getattr(settings, "JWT_COOKIE_SECURE", not settings.DEBUG)
        samesite = getattr(settings, "JWT_COOKIE_SAMESITE", "Lax")
        access_max_age = int(
            settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
        )

        response = JsonResponse({"success": True})
        response.set_cookie(
            jwt_service.access_cookie,
            access,
            max_age=access_max_age,
            httponly=True,
            secure=secure_flag,
            samesite=samesite,
            path="/",
        )
        if rotated:
            refresh_max_age = int(
                settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
            )
            response.set_cookie(
                jwt_service.refresh_cookie,
                rotated,
                max_age=refresh_max_age,
                httponly=True,
                secure=secure_flag,
                samesite=samesite,
                path=jwt_service.refresh_cookie_path,
            )
        return response


class WebLogoutView(View):
    """Clear Django session, revoke JWT refresh token, and remove auth cookies."""

    http_method_names = ["get", "post"]

    def get(self, request):
        return self._logout(request)

    def post(self, request):
        return self._logout(request)

    def _logout(self, request):
        jwt_service = WebJWTService()
        refresh = request.COOKIES.get(jwt_service.refresh_cookie)
        meta = {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        }
        jwt_service.logout(refresh_token=refresh, request_meta=meta)
        SessionService().logout(request)

        response = redirect(reverse("home"))
        jwt_service.clear_tokens(response)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
