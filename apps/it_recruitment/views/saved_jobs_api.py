"""Saved jobs JSON API for the job seeker portal."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.it_recruitment.models import JobSeekerProfile
from apps.jobs.services.saved_job_service import SavedJobService


def _get_profile(user) -> JobSeekerProfile | None:
    return JobSeekerProfile.objects.filter(user=user, is_deleted=False).first()


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


class JobSeekerSavedJobsAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"

    def get(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return _forbidden()
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        page = max(1, int(request.GET.get("page") or 1))
        result = SavedJobService().list_saved(profile, page=page)
        return JsonResponse(
            {
                "success": True,
                "data": result.to_dict(),
                "saved_count": result.total_count,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerSavedJobToggleAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def post(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return _forbidden()
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        job_id = request.POST.get("job_id")
        if not job_id:
            return JsonResponse(
                {"success": False, "error": "job_id is required."}, status=400
            )

        try:
            result = SavedJobService().toggle(profile, job_id)
            return JsonResponse({"success": True, "data": result.to_dict()})
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=404)
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


class JobSeekerSavedJobStatusAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"

    def get(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return _forbidden()
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        raw = request.GET.get("ids") or ""
        job_ids = [part.strip() for part in raw.split(",") if part.strip()]
        status = SavedJobService().status_map(profile, job_ids)
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "status": status,
                    "saved_count": SavedJobService().count(profile),
                },
            }
        )
