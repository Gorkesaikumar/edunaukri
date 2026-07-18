"""Resume portal JSON API for job seekers."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_resume_portal_service import (
    JobSeekerResumePortalService,
)
from apps.it_recruitment.services.resume_autofill_service import ResumeAutofillService


def _get_profile(user) -> JobSeekerProfile | None:
    return (
        JobSeekerProfile.objects.filter(user=user, is_deleted=False)
        .select_related("resume_file")
        .first()
    )


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerResumePortalAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"

    def get(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
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


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerResumeAutofillAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def post(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        fields = request.POST.getlist("fields") or None
        try:
            result = ResumeAutofillService().apply(
                profile, actor_id=request.user.pk, fields=fields
            )
            return JsonResponse(
                {
                    "success": True,
                    "data": result,
                    "message": "Profile updated from resume.",
                }
            )
        except ValidationException as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
