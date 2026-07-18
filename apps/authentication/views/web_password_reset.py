"""Web password reset — shared IT and Faculty domain flows."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views import View

from apps.authentication.services.password_reset_service import PasswordResetService
from apps.authentication.views.web_auth_helpers import format_validation_errors
from apps.authentication.views.web_auth_context import resolve_auth_portal_context

logger = logging.getLogger(__name__)

SUPPORTED_DOMAINS = frozenset({"it", "professor", "college"})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
@method_decorator(ratelimit(key="post:email", rate="3/m", block=True), name="post")
class WebForgotPasswordView(View):
    http_method_names = ["get", "post"]

    def get(self, request):
        context = resolve_auth_portal_context(request, page="forgot_password")
        if context["domain"] not in SUPPORTED_DOMAINS:
            context["domain"] = "it"
        return render(request, "auth/forgot_password.html", context)

    def post(self, request):
        domain = (request.POST.get("domain") or "it").strip()
        email = (request.POST.get("email") or "").strip()

        if domain not in SUPPORTED_DOMAINS:
            return JsonResponse(
                {"success": False, "errors": {"form": "Unsupported account domain."}},
                status=400,
            )
        if not email:
            return JsonResponse(
                {"success": False, "errors": {"email": "Email address is required."}},
                status=400,
            )

        try:
            PasswordResetService().request_reset(domain=domain, email=email)
        except ValidationError as exc:
            errors = format_validation_errors(exc)
            return JsonResponse({"success": False, "errors": errors}, status=400)
        except Exception:
            logger.exception("Password reset request failed for domain=%s", domain)

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "If an account exists for that email, you will receive password reset instructions shortly."
                ),
            }
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class WebResetPasswordView(View):
    http_method_names = ["get", "post"]

    def get(self, request):
        context = resolve_auth_portal_context(request, page="reset_password")
        context["token"] = (request.GET.get("token") or "").strip()
        if context["domain"] not in SUPPORTED_DOMAINS:
            context["domain"] = "it"
        return render(request, "auth/reset_password.html", context)

    def post(self, request):
        domain = (request.POST.get("domain") or "it").strip()
        token = (request.POST.get("token") or "").strip()
        password = request.POST.get("password") or ""
        confirm = request.POST.get("confirm_password") or ""

        errors: dict[str, str] = {}
        if domain not in SUPPORTED_DOMAINS:
            errors["form"] = "Unsupported account domain."
        if not token:
            errors["form"] = errors.get("form") or "Reset token is missing or invalid."
        if not password:
            errors["password"] = "Password is required."
        if not confirm:
            errors["confirm_password"] = "Please confirm your password."
        elif password and password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        try:
            PasswordResetService().confirm_reset(
                domain=domain, token=token, new_password=password
            )
        except ValidationError as exc:
            formatted = format_validation_errors(exc)
            return JsonResponse({"success": False, "errors": formatted}, status=400)
        except Exception:
            logger.exception("Password reset confirm failed for domain=%s", domain)
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": "Unable to reset password. Please try again."},
                },
                status=500,
            )

        context = resolve_auth_portal_context(
            request, page="reset_password", domain=domain
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Your password has been updated. You can sign in now.",
                "redirect_url": context["login_url"],
            }
        )
