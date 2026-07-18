"""JSON API for institution dashboard live insights."""

from __future__ import annotations

from django.http import JsonResponse

from apps.accounts.models.college_user import CollegeUser
from apps.academic_recruitment.services.college_dashboard_portal_service import (
    CollegeDashboardPortalService,
)
from apps.academic_recruitment.views.college_api_base import CollegeScopedAPIView
from apps.authentication.services.portal_url_service import PortalURLService


class CollegeDashboardInsightsAPIView(CollegeScopedAPIView):
    def get(self, request, **kwargs):
        if not isinstance(request.user, CollegeUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        if request.GET.get("live") == "1":
            from apps.notifications.services.outbox_processor import (
                OutboxProcessorService,
            )

            OutboxProcessorService().process_batch(limit=25)

        user = request.user
        dashboard = CollegeDashboardPortalService().build(user=user)
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        placeholder = "00000000-0000-0000-0000-000000000000"

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "greeting": dashboard.get("greeting"),
                    "display_name": dashboard.get("display_name"),
                    "headline": dashboard.get("headline"),
                    "subheadline": dashboard.get("subheadline"),
                    "stats": dashboard.get("stats", []),
                    "overview_stats": dashboard.get("overview_stats", []),
                    "pipeline": dashboard.get("pipeline", []),
                    "pipeline_view": dashboard.get("pipeline_view", []),
                    "recent_applications": dashboard.get("recent_applications", []),
                    "active_vacancies": dashboard.get("active_vacancies", []),
                    "upcoming_interviews": dashboard.get("upcoming_interviews", []),
                    "offer_management": dashboard.get("offer_management", {}),
                    "notifications": dashboard.get("notifications", []),
                    "messages": dashboard.get("messages", {}),
                    "profile_analytics": dashboard.get("profile_analytics", {}),
                    "institution_profile": dashboard.get("institution_profile", {}),
                    "quick_actions": dashboard.get("quick_actions", []),
                    "has_institution": dashboard.get("has_institution", False),
                    "api_urls": {
                        "status_template": pu(
                            "college_application_status_api", application_id=placeholder
                        ),
                        "notes_template": pu(
                            "college_application_notes_api", application_id=placeholder
                        ),
                        "detail_template": pu(
                            "college_application_detail", application_id=placeholder
                        ),
                        "cv_template": pu(
                            "college_application_cv_api", application_id=placeholder
                        ),
                    },
                },
            }
        )


from apps.academic_recruitment.services.college_analytics_portal_service import (
    CollegeAnalyticsPortalService,
)


class CollegeAnalyticsInsightsAPIView(CollegeScopedAPIView):
    def get(self, request, **kwargs):
        if not isinstance(request.user, CollegeUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        period = request.GET.get("analytics_period", "8w")

        try:
            analytics_page = CollegeAnalyticsPortalService().build(
                user=request.user, period=period
            )

            data = {
                "stats": analytics_page.stats,
                "reporting": analytics_page.reporting,
                "funnel": analytics_page.funnel,
                "vacancy_performance": analytics_page.vacancy_performance,
                "application_sources": analytics_page.application_sources,
                "trends": analytics_page.trends,
                "department_hiring": analytics_page.department_hiring,
                "response_rate": analytics_page.response_rate,
            }
            return JsonResponse({"success": True, "data": data})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


class CollegeProfileCompletionAnimationAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        if not isinstance(request.user, CollegeUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        from apps.colleges.selectors.college_selector import CollegeMemberSelector
        membership = CollegeMemberSelector().primary_for_user(request.user)
        if not membership:
            return JsonResponse({"success": False, "error": "No primary institution found."}, status=404)

        from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
        CollegeProfileCompletionService().mark_celebration_shown(membership.college)

        return JsonResponse({"success": True})
