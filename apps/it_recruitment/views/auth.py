"""IT domain web authentication — role-based session login."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.authentication.views.web_auth_helpers import (
    format_validation_errors,
    safe_next_url,
    validate_login_credentials,
)
from apps.it_recruitment.services.web_registration_service import (
    ITWebRegistrationService,
)

logger = logging.getLogger(__name__)


def _login_page_context(active_role: str, request=None) -> dict:
    """Shared template context for the IT login page."""
    next_url = safe_next_url(request) if request is not None else ""
    return {
        "active_role": active_role,
        "next_url": next_url,
        "page_urls": {
            "seeker": reverse("it_login_job_seeker"),
            "recruiter": reverse("it_login_recruiter"),
        },
        "login_endpoints": {
            "seeker": reverse("it_login_job_seeker"),
            "recruiter": reverse("it_login_recruiter"),
        },
        "oauth_endpoints": {
            "google": reverse("oauth_google"),
            "linkedin": reverse("oauth_linkedin"),
        },
        "signup_urls": {
            "seeker": reverse("it_signup_job_seeker"),
            "recruiter": reverse("it_signup_recruiter"),
        },
    }


@method_decorator(ratelimit(key="ip", rate="15/m", block=True), name="post")
@method_decorator(ratelimit(key="post:email", rate="5/m", block=True), name="post")
class _ITRoleLoginView(View):
    """Role-specific IT login — GET renders the page, POST authenticates."""

    http_method_names = ["get", "post"]
    active_role: str = "seeker"
    role: str = ""
    role_label: str = ""
    dashboard_url_name: str = ""

    def get(self, request, *args, **kwargs):
        return render(
            request,
            "auth/it_login.html",
            _login_page_context(self.active_role, request),
        )

    def post(self, request, *args, **kwargs):
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        next_url = safe_next_url(request)

        errors = validate_login_credentials(email, password)
        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        try:
            user = SessionService().login(
                request, domain="it", email=email, password=password
            )
            roles = RoleAssignmentService()
            if not roles.user_has_it_role(user, self.role):
                SessionService().logout(request)
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            "form": f"This account is not registered as a {self.role_label}. "
                            f"Switch to the correct account type and try again."
                        },
                    },
                    status=403,
                )
            redirect_target = next_url or PortalURLService.dashboard_for_user(user)
            response = JsonResponse({"success": True, "redirect_url": redirect_target})
            return WebJWTService().attach_tokens_with_request(
                response, user=user, domain="it", request=request
            )
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse(
                {"success": False, "errors": {"form": message}}, status=401
            )
        except Exception:
            logger.exception("IT login failed for role=%s email=%s", self.role, email)
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": "Unable to sign in. Please try again."},
                },
                status=500,
            )


class ITJobSeekerLoginView(_ITRoleLoginView):
    active_role = "seeker"
    role = ITUserRoleType.JOB_SEEKER
    role_label = "Job Seeker"
    dashboard_url_name = "jobseeker_dashboard"


class ITRecruiterLoginView(_ITRoleLoginView):
    active_role = "recruiter"
    role = ITUserRoleType.RECRUITER
    role_label = "Recruiter"
    dashboard_url_name = "recruiter_dashboard"


class ITLoginView(TemplateView):
    """Default IT login entry — redirects to Job Seeker login."""

    def get(self, request, *args, **kwargs):
        return redirect("it_login_job_seeker")


def _signup_page_context(active_role: str) -> dict:
    """Shared template context for the IT signup page."""
    return {
        "active_role": active_role,
        "signup_endpoints": {
            "seeker": reverse("it_signup_job_seeker"),
            "recruiter": reverse("it_signup_recruiter"),
        },
        "login_urls": {
            "seeker": reverse("it_login_job_seeker"),
            "recruiter": reverse("it_login_recruiter"),
        },
        "oauth_endpoints": {
            "google": reverse("oauth_google"),
            "linkedin": reverse("oauth_linkedin"),
        },
        "check_email_url": reverse("it_signup_check_email"),
    }


@method_decorator(ratelimit(key="ip", rate="30/m", block=True), name="get")
class ITSignupCheckEmailView(View):
    """Lightweight duplicate-email check for signup forms."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        email = (request.GET.get("email") or "").strip()
        if not email:
            return JsonResponse(
                {"available": False, "message": "Email is required."}, status=400
            )
        exists = ITWebRegistrationService().email_exists(email)
        return JsonResponse(
            {
                "available": not exists,
                "message": "An account with this email already exists."
                if exists
                else "",
            }
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class _ITRoleSignupView(View):
    """Role-specific IT signup — GET renders the page, POST registers."""

    http_method_names = ["get", "post"]
    active_role: str = "seeker"
    role_label: str = ""
    login_url_name: str = "it_login_job_seeker"
    dashboard_url_name: str = "jobseeker_dashboard"

    def get(self, request, *args, **kwargs):
        return render(
            request, "auth/it_signup.html", _signup_page_context(self.active_role)
        )

    def post(self, request, *args, **kwargs):
        data = {key: request.POST.get(key, "") for key in request.POST}

        try:
            service = ITWebRegistrationService()
            role = (data.get("role") or self.active_role or "seeker").strip()
            if role == "recruiter":
                result = service.register_recruiter(request, data=data)
            else:
                result = service.register_job_seeker(request, data=data)

            if not result.get("redirect_url"):
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {"form": "Unable to complete registration. Please try again."},
                    },
                    status=500
                )
            response = JsonResponse(
                {
                    "success": True,
                    "redirect_url": result["redirect_url"],
                    "message": "Registration successful.",
                }
            )
            if result.get("user"):
                WebJWTService().attach_tokens_with_request(
                    response, user=result["user"], domain="it", request=request
                )
            return response
        except ValidationError as exc:
            errors = format_validation_errors(exc)
            return JsonResponse({"success": False, "errors": errors}, status=400)
        except ValidationException as exc:
            return JsonResponse(
                {"success": False, "errors": {"form": str(exc)}}, status=400
            )
        except Exception:
            logger.exception("IT signup failed for role=%s", self.active_role)
            return JsonResponse(
                {
                    "success": False,
                    "errors": {
                        "form": "Unable to complete registration. Please try again."
                    },
                },
                status=500,
            )


class ITJobSeekerSignupView(_ITRoleSignupView):
    active_role = "seeker"
    role_label = "Job Seeker"
    login_url_name = "it_login_job_seeker"
    dashboard_url_name = "jobseeker_dashboard"


class ITRecruiterSignupView(_ITRoleSignupView):
    active_role = "recruiter"
    role_label = "Recruiter"
    login_url_name = "it_login_recruiter"
    dashboard_url_name = "recruiter_dashboard"


class ITSignupView(View):
    """Default IT signup entry — redirects to Job Seeker signup."""

    def get(self, request, *args, **kwargs):
        return redirect("it_signup_job_seeker")
