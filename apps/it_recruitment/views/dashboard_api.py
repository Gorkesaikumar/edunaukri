"""JSON API for job seeker dashboard insights and profile completion."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.dashboard_recommendation_engine import (
    DashboardRecommendationEngine,
)
from apps.it_recruitment.services.job_recommendation_engine_service import (
    JobRecommendationEngineService,
)
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_dashboard_service import (
    JobSeekerDashboardService,
)
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.it_recruitment.services.recruiter_dashboard_service import (
    RecruiterDashboardService,
)
from apps.it_recruitment.views.recruiter_api_base import RecruiterScopedAPIView


def _get_seeker_profile(user) -> JobSeekerProfile | None:
    return (
        JobSeekerProfile.objects.filter(user=user, is_deleted=False)
        .select_related("profile_photo", "resume_file")
        .prefetch_related("skills__skill", "experiences", "education")
        .first()
    )


class JobSeekerDashboardInsightsAPIView(LoginRequiredMixin, View):
    """Return hero card insights, completion, and recommendations for the authenticated seeker."""

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

        completion_service = JobSeekerProfileCompletionService()
        if request.GET.get("refresh") == "1":
            completion_state = completion_service.recalculate(profile)
        else:
            completion_state = completion_service.get_dashboard_state(profile)

        hero = DashboardRecommendationEngine().build(profile)
        rec_engine = JobRecommendationEngineService()

        if request.GET.get("live") == "1":
            from apps.notifications.services.outbox_processor import (
                OutboxProcessorService,
            )
            from apps.it_recruitment.services.job_recommendation_cache_service import (
                JobRecommendationCacheService,
            )

            OutboxProcessorService().process_batch(limit=25)
            snapshot = JobRecommendationCacheService().get_snapshot(profile)
            now = timezone.now()
            stale = (
                snapshot is None
                or snapshot.computed_at is None
                or (now - snapshot.computed_at).total_seconds() > 600
            )
            if stale:
                rec_engine.rebuild_for_seeker(
                    profile.pk,
                    reason="dashboard_live",
                    notify=False,
                )

        dashboard = JobSeekerDashboardService().build(
            user=request.user, profile=profile
        )
        recommendations = rec_engine.get_recommendations(profile, limit=8)
        kpis = dashboard.kpis.to_dict() if dashboard.kpis else None

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "hero": hero.to_dict() if hero else None,
                    "completion": completion_state.to_dict(),
                    "profile_completion": completion_state.to_dict(),
                    "recommendations": recommendations.to_dict(),
                    "kpis": kpis,
                    "stats": [stat.to_dict() for stat in dashboard.stats],
                    "recommended_jobs": [
                        {
                            "id": job.id,
                            "title": job.title,
                            "company_name": job.company_name,
                            "match_percent": job.match_percent,
                            "detail_url": job.detail_url,
                        }
                        for job in dashboard.recommended_jobs
                    ],
                },
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileCompletionAnimationAPIView(LoginRequiredMixin, View):
    """Mark the one-time profile completion celebration as shown."""

    login_url = "/it/login/job-seeker/"

    def post(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        profile = _get_seeker_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        completion_state = JobSeekerProfileCompletionService().mark_celebration_shown(
            profile
        )
        return JsonResponse({"success": True, "data": completion_state.to_dict()})


def _get_recruiter_profile(user) -> RecruiterProfile | None:
    return RecruiterProfile.objects.filter(user=user, is_deleted=False).first()


class RecruiterDashboardInsightsAPIView(RecruiterScopedAPIView):
    """Return live KPIs and dashboard widgets for the authenticated recruiter."""

    def get(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.RECRUITER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        profile = _get_recruiter_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        if request.GET.get("live") == "1":
            from apps.notifications.services.outbox_processor import (
                OutboxProcessorService,
            )

            OutboxProcessorService().process_batch(limit=25)

        from apps.it_recruitment.services.recruiter_dashboard_widgets_service import (
            DashboardFilters,
        )

        filters = DashboardFilters.from_request(request)
        dashboard = RecruiterDashboardService().build(profile, filters=filters)
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "greeting": dashboard.greeting,
                    "recruiter_name": dashboard.recruiter_name,
                    "hero_insight": dashboard.hero_insight,
                    "hero_insight_key": dashboard.hero_insight_key,
                    "company_card": dashboard.company_card,
                    "new_applications_today": dashboard.new_applications_today,
                    "welcome_message": dashboard.welcome_message,
                    "stats": dashboard.stats,
                    "pipeline": dashboard.pipeline,
                    "active_jobs": dashboard.active_jobs,
                    "upcoming_interviews": dashboard.upcoming_interviews,
                    "interviews_today": dashboard.interviews_today,
                    "candidate_sources": dashboard.candidate_sources,
                    "recent_applications": dashboard.recent_applications,
                    "recent_activity": dashboard.recent_activity,
                    "notifications": dashboard.notifications,
                    "analytics": dashboard.analytics,
                    "filters": dashboard.filters,
                    "api_urls": dashboard.api_urls,
                },
            }
        )


class RecruiterAnalyticsExportAPIView(RecruiterScopedAPIView):
    """Export recruitment analytics as CSV, Excel-compatible CSV, or printable HTML (PDF)."""

    def get(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.RECRUITER
        ):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        profile = _get_recruiter_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        from apps.it_recruitment.services.recruiter_analytics_section_service import (
            AnalyticsPeriod,
            RecruiterAnalyticsSectionService,
        )

        period = AnalyticsPeriod.from_request(request)
        fmt = (request.GET.get("format") or "csv").lower()
        service = RecruiterAnalyticsSectionService()
        rows = service.export_rows(profile, period)

        if fmt == "pdf":
            html_rows = "".join(
                f"<tr>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>"
                for row in rows
                if row
            )
            html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Analytics Export</title>
            <style>body{{font-family:Arial,sans-serif;padding:24px}}table{{border-collapse:collapse;width:100%}}
            td,th{{border:1px solid #ddd;padding:8px;font-size:12px}}</style></head>
            <body><h1>Recruitment Analytics — {period.label}</h1><table>{html_rows}</table>
            <script>window.onload=function(){{window.print()}}</script></body></html>"""
            from django.http import HttpResponse

            return HttpResponse(html, content_type="text/html")

        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        for row in rows:
            writer.writerow(row)
        content = output.getvalue()
        from django.http import HttpResponse

        if fmt in ("xlsx", "excel"):
            response = HttpResponse(content, content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                f'attachment; filename="recruitment-analytics-{period.key}.xls"'
            )
            return response

        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="recruitment-analytics-{period.key}.csv"'
        )
        return response
