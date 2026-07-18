"""JSON API for faculty job seeker dashboard insights."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_dashboard_kpi_service import (
    ProfessorDashboardKPIService,
)
from apps.academic_recruitment.services.professor_dashboard_portal_service import (
    ProfessorDashboardPortalService,
)
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)


def _get_profile(user) -> ProfessorProfile | None:
    if not isinstance(user, ProfessorUser):
        return None
    return (
        ProfessorProfile.objects.filter(user=user, is_deleted=False)
        .select_related("profile_photo", "cv_file", "user")
        .prefetch_related("qualifications", "departments__department")
        .first()
    )


class ProfessorDashboardInsightsAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _get_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        completion_service = ProfessorProfileCompletionService()
        if request.GET.get("refresh") == "1":
            from apps.accounts.profiles.constants.enums import ProfileType
            from apps.accounts.profiles.services.profile_completion_service import (
                ProfileCompletionService,
            )

            pct = ProfileCompletionService().calculate(profile, ProfileType.PROFESSOR)
            completion_state = ProfessorProfileCompletionService().get_dashboard_state(
                profile
            )
            completion_state.percentage = pct
        else:
            completion_state = completion_service.get_dashboard_state(profile)

        if request.GET.get("live") == "1":
            from apps.notifications.services.outbox_processor import (
                OutboxProcessorService,
            )

            OutboxProcessorService().process_batch(limit=25)

        dashboard = ProfessorDashboardPortalService().build(
            user=request.user, profile=profile
        )
        kpis = ProfessorDashboardKPIService().build(profile)

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "completion": completion_state.to_dict(),
                    "profile_completion": completion_state.to_dict(),
                    "kpis": kpis.to_dict(),
                    "stats": dashboard.get("stats", []),
                    "tracker_stats": dashboard.get("tracker_stats", []),
                    "recommended_jobs": dashboard.get("recommended_jobs", []),
                    "unread_notification_count": dashboard.get(
                        "unread_notification_count", 0
                    ),
                    "saved_jobs_count": dashboard.get("saved_jobs_count", 0),
                },
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfileCompletionAnimationAPIView(LoginRequiredMixin, View):
    """Mark profile completion celebration as shown after confetti animation."""

    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        profile = _get_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        completion_state = ProfessorProfileCompletionService().mark_celebration_shown(
            profile
        )
        return JsonResponse({"success": True, "data": completion_state.to_dict()})


class ProfessorRecommendedJobsPartialAPIView(LoginRequiredMixin, View):
    """Efficient HTML partial polling endpoint for real-time job recommendations."""

    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _get_profile(request.user)
        if profile is None:
            return JsonResponse({"success": False}, status=404)

        dashboard_svc = ProfessorDashboardPortalService()
        recommended_jobs = dashboard_svc._recommended_jobs(profile, request.user)
        
        from django.template.loader import render_to_string
        html = render_to_string(
            "academic/professor/dashboard/partials/recommended_jobs.html",
            {"dashboard": {"recommended_jobs": [j.to_dict() for j in recommended_jobs]}},
            request=request
        )

        return JsonResponse({"success": True, "html": html})
