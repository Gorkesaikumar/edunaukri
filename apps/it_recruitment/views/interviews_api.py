"""Job seeker interview portal API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_interview_portal_service import (
    JobSeekerInterviewPortalService,
)


def _get_profile(user) -> JobSeekerProfile | None:
    return JobSeekerProfile.objects.filter(user=user, is_deleted=False).first()


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerInterviewConfirmAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        try:
            JobSeekerInterviewPortalService().confirm_attendance(
                profile, application_id, actor=request.user
            )
            return JsonResponse(
                {"success": True, "message": "Attendance confirmed successfully."}
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerInterviewRescheduleAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        reason = request.POST.get("reason", "")
        try:
            JobSeekerInterviewPortalService().request_reschedule(
                profile, application_id, actor=request.user, reason=reason
            )
            return JsonResponse(
                {"success": True, "message": "Reschedule request sent to recruiter."}
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


class JobSeekerInterviewsAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"

    def get(self, request, *args, **kwargs):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        result = JobSeekerInterviewPortalService().list_interviews(
            profile,
            q=(request.GET.get("q") or "").strip(),
            status_filter=(request.GET.get("status") or "").strip(),
            when=(request.GET.get("when") or "").strip(),
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "summary": [
                        {"key": s.key, "label": s.label, "value": s.value}
                        for s in result.summary
                    ],
                    "analytics": result.analytics,
                },
            }
        )
