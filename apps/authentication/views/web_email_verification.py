"""Web email verification — shared IT and Faculty domain flows."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views import View

from apps.authentication.services.email_verification_service import (
    EmailVerificationService,
)
from apps.authentication.views.web_auth_context import resolve_auth_portal_context
from apps.core.exceptions.domain_exceptions import ValidationException

logger = logging.getLogger(__name__)

SUPPORTED_DOMAINS = frozenset({"it", "professor", "college"})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
@method_decorator(ratelimit(key="ip", rate="20/m", block=True), name="get")
class WebEmailVerificationView(View):
    http_method_names = ["get", "post"]

    def get(self, request):
        context = resolve_auth_portal_context(request, page="verify_email")
        context["token"] = (request.GET.get("token") or "").strip()
        if context["domain"] not in SUPPORTED_DOMAINS:
            context["domain"] = "it"
        context["verified"] = False
        context["error_message"] = ""

        if context["token"] and context["domain"] in SUPPORTED_DOMAINS:
            try:
                EmailVerificationService().verify(
                    domain=context["domain"], token=context["token"]
                )
                context["verified"] = True
            except (ValidationError, ValidationException) as exc:
                message = (
                    exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                )
                context["error_message"] = message
            except Exception:
                logger.exception(
                    "Email verification failed for domain=%s", context["domain"]
                )
                context["error_message"] = "Unable to verify email. Please try again."

        return render(request, "auth/verify_email.html", context)

    def post(self, request):
        domain = (
            request.POST.get("domain") or request.GET.get("domain") or "it"
        ).strip()
        token = (request.POST.get("token") or request.GET.get("token") or "").strip()

        if domain not in SUPPORTED_DOMAINS or not token:
            return JsonResponse(
                {"success": False, "errors": {"form": "Invalid verification link."}},
                status=400,
            )

        try:
            EmailVerificationService().verify(domain=domain, token=token)
        except (ValidationError, ValidationException) as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse(
                {"success": False, "errors": {"form": message}}, status=400
            )
        except Exception:
            logger.exception("Email verification failed for domain=%s", domain)
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": "Unable to verify email. Please try again."},
                },
                status=500,
            )

        context = resolve_auth_portal_context(
            request, page="verify_email", domain=domain
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Your email has been verified. You can sign in now.",
                "redirect_url": context["login_url"],
            }
        )
