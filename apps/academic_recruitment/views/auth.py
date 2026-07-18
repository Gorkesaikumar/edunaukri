"""Faculty domain web authentication — professor and institution login/signup."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.views import View

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.services.web_registration_service import (
    FacultyWebRegistrationService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.authentication.views.web_auth_helpers import (
    format_validation_errors,
    safe_next_url,
    validate_login_credentials,
)
from apps.core.exceptions.domain_exceptions import ValidationException

logger = logging.getLogger(__name__)


def _login_page_context(active_role: str, request=None) -> dict:
    next_url = safe_next_url(request) if request is not None else ""
    return {
        "active_role": active_role,
        "next_url": next_url,
        "page_urls": {
            "seeker": reverse("faculty_login_professor"),
            "institution": reverse("faculty_login_institution"),
        },
        "login_endpoints": {
            "seeker": reverse("faculty_login_professor"),
            "institution": reverse("faculty_login_institution"),
        },
        "signup_urls": {
            "seeker": reverse("faculty_signup_professor"),
            "institution": reverse("faculty_signup_institution"),
        },
        "oauth_endpoints": {
            "google": reverse("oauth_google"),
            "linkedin": reverse("oauth_linkedin"),
        },
    }


@method_decorator(ratelimit(key="ip", rate="15/m", block=True), name="post")
@method_decorator(ratelimit(key="post:email", rate="5/m", block=True), name="post")
class _FacultyRoleLoginView(View):
    """Role-specific faculty login — GET renders the page, POST authenticates."""

    http_method_names = ["get", "post"]
    active_role: str = "seeker"
    auth_domain: str = "professor"
    role_label: str = ""
    user_model = ProfessorUser

    def get(self, request):
        return render(
            request,
            "auth/faculty_login.html",
            _login_page_context(self.active_role, request),
        )

    def post(self, request):
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        next_url = safe_next_url(request)

        errors = validate_login_credentials(email, password)
        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        try:
            user = SessionService().login(
                request,
                domain=self.auth_domain,
                email=email,
                password=password,
            )
            if not isinstance(user, self.user_model):
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
                response,
                user=user,
                domain=self.auth_domain,
                request=request,
            )
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse(
                {"success": False, "errors": {"form": message}}, status=401
            )
        except Exception:
            logger.exception(
                "Faculty login failed for domain=%s email=%s", self.auth_domain, email
            )
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": "Unable to sign in. Please try again."},
                },
                status=500,
            )


class FacultyProfessorLoginView(_FacultyRoleLoginView):
    active_role = "seeker"
    auth_domain = "professor"
    role_label = "Faculty Job Seeker"
    user_model = ProfessorUser


class FacultyInstitutionLoginView(_FacultyRoleLoginView):
    active_role = "institution"
    auth_domain = "college"
    role_label = "Institution"
    user_model = CollegeUser


class FacultyLoginView(View):
    """Default faculty login entry — redirects to Faculty Job Seeker login."""

    def get(self, request, *args, **kwargs):
        return redirect("faculty_login_professor")


def _signup_page_context(active_role: str) -> dict:
    return {
        "active_role": active_role,
        "signup_endpoints": {
            "seeker": reverse("faculty_signup_professor"),
            "institution": reverse("faculty_signup_institution"),
        },
        "login_urls": {
            "seeker": reverse("faculty_login_professor"),
            "institution": reverse("faculty_login_institution"),
        },
        "oauth_endpoints": {
            "google": reverse("oauth_google"),
            "linkedin": reverse("oauth_linkedin"),
        },
        "check_email_url": reverse("faculty_signup_check_email"),
    }


@method_decorator(ratelimit(key="ip", rate="30/m", block=True), name="get")
class FacultySignupCheckEmailView(View):
    http_method_names = ["get"]

    def get(self, request):
        email = (request.GET.get("email") or "").strip()
        role = (request.GET.get("role") or "seeker").strip()
        if role not in {"seeker", "institution"}:
            role = "seeker"
        if not email:
            return JsonResponse(
                {"available": False, "message": "Email is required."}, status=400
            )
        exists = FacultyWebRegistrationService().email_exists(email, role=role)
        return JsonResponse(
            {
                "available": not exists,
                "message": "An account with this email already exists."
                if exists
                else "",
            }
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class _FacultyRoleSignupView(View):
    http_method_names = ["get", "post"]
    active_role: str = "seeker"
    role_label: str = ""
    login_url_name: str = "faculty_login_professor"

    def get(self, request):
        return render(
            request, "auth/faculty_signup.html", _signup_page_context(self.active_role)
        )

    def post(self, request):
        data = {}
        for key in request.POST:
            vals = [
                v.strip()
                for v in request.POST.getlist(key)
                if v is not None and str(v).strip()
            ]
            data[key] = vals[0] if vals else (request.POST.get(key, "") or "").strip()

        role = (data.get("role") or self.active_role or "seeker").strip()
        if (
            role == "institution"
            and not data.get("email")
            and data.get("institution_email")
        ):
            data["email"] = data["institution_email"]

        try:
            service = FacultyWebRegistrationService()
            if role == "institution":
                result = service.register_institution(request, data=data)
                domain = "college"
            else:
                result = service.register_professor(request, data=data)
                domain = "professor"

            if result.get("requires_verification") or not result.get("redirect_url"):
                return JsonResponse(
                    {
                        "success": True,
                        "requires_verification": True,
                        "redirect_url": reverse(self.login_url_name),
                        "message": "Registration successful. Please verify your email before signing in.",
                    }
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
                    response,
                    user=result["user"],
                    domain=domain,
                    request=request,
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
            logger.exception("Faculty signup failed for role=%s", self.active_role)
            return JsonResponse(
                {
                    "success": False,
                    "errors": {
                        "form": "Unable to complete registration. Please try again."
                    },
                },
                status=500,
            )


class FacultyProfessorSignupView(_FacultyRoleSignupView):
    active_role = "seeker"
    role_label = "Faculty Job Seeker"
    login_url_name = "faculty_login_professor"


class FacultyInstitutionSignupView(_FacultyRoleSignupView):
    active_role = "institution"
    role_label = "Institution"
    login_url_name = "faculty_login_institution"


class FacultySignupView(View):
    """Default faculty signup entry — redirects to Faculty Job Seeker signup."""

    def get(self, request, *args, **kwargs):
        return redirect("faculty_signup_professor")
