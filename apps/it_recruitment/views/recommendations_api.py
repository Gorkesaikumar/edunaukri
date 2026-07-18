"""JSON API for cached job recommendations."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_recommendation_engine_service import (
    JobRecommendationEngineService,
)


def _get_seeker_profile(user) -> JobSeekerProfile | None:
    return (
        JobSeekerProfile.objects.filter(user=user, is_deleted=False)
        .select_related("profile_photo", "resume_file")
        .prefetch_related("skills__skill", "experiences", "education")
        .first()
    )


class JobSeekerRecommendationsAPIView(LoginRequiredMixin, View):
    """Return ranked job recommendations from the recommendation cache."""

    login_url = "/it/login/job-seeker/"

    def get(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        profile = _get_seeker_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        force = request.GET.get("refresh") == "1"
        limit = min(int(request.GET.get("limit", 20)), 50)
        summary = JobRecommendationEngineService().get_recommendations(
            profile,
            limit=limit,
            force_rebuild=force,
        )
        return JsonResponse({"success": True, "data": summary.to_dict()})
