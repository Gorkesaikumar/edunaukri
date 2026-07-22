"""Resume portal JSON API for job seekers."""

from __future__ import annotations

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.core.exceptions.domain_exceptions import DomainException, ValidationException
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_resume_portal_service import (
    JobSeekerResumePortalService,
)
from apps.it_recruitment.services.resume_autofill_service import ResumeAutofillService

logger = logging.getLogger(__name__)


def _get_profile(user) -> JobSeekerProfile | None:
    return (
        JobSeekerProfile.objects.filter(user=user, is_deleted=False)
        .select_related("resume_file")
        .first()
    )


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerResumePortalAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"

    def get(self, request, *args, **kwargs):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse(
                {"success": False, "message": "Permission denied.", "errors": {"detail": "Forbidden."}},
                status=403,
            )
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "message": "Profile not found.", "errors": {"detail": "Profile not found."}},
                status=404,
            )
        try:
            page = JobSeekerResumePortalService().build(profile)
            return JsonResponse(
                {
                    "success": True,
                    "data": {
                        "has_resume": page.has_resume,
                        "match_score": page.match_score,
                        "match_explanation": page.match_explanation,
                        "analytics": page.analytics,
                        "parsed": page.parsed,
                        "version": page.version,
                        "autofill_suggestions": page.autofill_suggestions,
                    },
                }
            )
        except Exception as exc:
            logger.exception("Error loading resume portal API data for user_id=%s: %s", request.user.pk, exc)
            return JsonResponse(
                {"success": False, "message": "Unable to fetch resume data.", "errors": {"detail": str(exc)}},
                status=500,
            )


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerResumeAutofillAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as exc:
            logger.exception("Error in autofill dispatch: %s", exc)
            return JsonResponse({"success": False, "message": "Server error in dispatch: " + str(exc)}, status=500)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "message": "Authentication required.", "errors": {"detail": "Unauthenticated."}},
                status=401,
            )

        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse(
                {"success": False, "message": "Permission denied.", "errors": {"detail": "Forbidden."}},
                status=403,
            )

        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "message": "Profile not found.", "errors": {"detail": "Job seeker profile not found."}},
                status=404,
            )

        fields = request.POST.getlist("fields") or None

        try:
            result = ResumeAutofillService().apply(
                profile, actor_id=request.user.pk, fields=fields
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": result.get("message") or "Profile updated successfully.",
                    "updated_sections": result.get("updated_sections") or [],
                },
                status=200,
            )
        except ValidationException as exc:
            logger.warning("Validation error in resume autofill for user_id=%s: %s", request.user.pk, exc)
            return JsonResponse(
                {
                    "success": False,
                    "message": str(exc) or "Unable to update profile.",
                    "errors": {"detail": str(exc)},
                },
                status=400,
            )
        except DomainException as exc:
            logger.warning("Domain exception in resume autofill for user_id=%s: %s", request.user.pk, exc)
            return JsonResponse(
                {
                    "success": False,
                    "message": str(exc) or "Unable to update profile.",
                    "errors": {"detail": str(exc)},
                },
                status=400,
            )
        except Exception as exc:
            logger.exception("Unexpected error in resume autofill for user_id=%s: %s", request.user.pk, exc)
            return JsonResponse(
                {
                    "success": False,
                    "message": "An error occurred while updating profile from resume.",
                    "errors": {"detail": "An internal server error occurred. Please try again."},
                },
                status=500,
            )
