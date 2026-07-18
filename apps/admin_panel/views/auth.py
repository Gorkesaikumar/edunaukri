"""Super Admin web authentication — enterprise login view."""

import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views import View

from apps.accounts.models.admin_user import AdminUser
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.authentication.views.web_auth_helpers import (
    safe_next_url,
    validate_login_credentials,
)

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
@method_decorator(ratelimit(key="post:email", rate="5/m", block=True), name="post")
class SuperAdminLoginView(View):
    """Super Admin login — GET renders enterprise login page, POST authenticates."""

    http_method_names = ["get", "post"]

    def get(self, request):
        user = WebJWTService.resolve_web_user(request)
        if user is not None and isinstance(user, AdminUser):
            return redirect(PortalURLService.super_admin(user, "super_admin_dashboard"))
        next_url = safe_next_url(request)
        context = {
            "next_url": next_url,
            "login_endpoint": reverse("super_admin_login"),
        }
        return render(request, "super_admin/auth/login.html", context)

    def post(self, request):
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        next_url = safe_next_url(request)

        errors = validate_login_credentials(email, password)
        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        try:
            user = SessionService().login(
                request, domain="admin", email=email, password=password
            )
            if not isinstance(user, AdminUser):
                SessionService().logout(request)
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {"form": "Invalid administrator credentials."},
                    },
                    status=403,
                )
            redirect_target = next_url or PortalURLService.super_admin(
                user, "super_admin_dashboard"
            )
            response = JsonResponse({"success": True, "redirect_url": redirect_target})
            return WebJWTService().attach_tokens_with_request(
                response, user=user, domain="admin", request=request
            )
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse(
                {"success": False, "errors": {"form": message}}, status=401
            )
        except Exception:
            logger.exception("Super Admin login failed for email=%s", email)
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": "Unable to sign in. Please try again."},
                },
                status=500,
            )
