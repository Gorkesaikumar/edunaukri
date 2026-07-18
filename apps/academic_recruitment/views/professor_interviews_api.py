"""Professor interview portal API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_interview_portal_service import (
    ProfessorInterviewPortalService,
)


def _get_profile(user) -> ProfessorProfile | None:
    return ProfessorProfile.objects.filter(user=user, is_deleted=False).first()


@method_decorator(csrf_protect, name="dispatch")
class ProfessorInterviewConfirmAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        if not isinstance(request.user, ProfessorUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        try:
            ProfessorInterviewPortalService().confirm_attendance(
                profile, application_id, actor=request.user
            )
            return JsonResponse(
                {"success": True, "message": "Attendance confirmed successfully."}
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorInterviewRescheduleAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        if not isinstance(request.user, ProfessorUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        reason = request.POST.get("reason", "")
        try:
            ProfessorInterviewPortalService().request_reschedule(
                profile, application_id, actor=request.user, reason=reason
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Reschedule request sent to the institution.",
                }
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
