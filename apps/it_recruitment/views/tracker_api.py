"""Job seeker career tracker API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_tracker_service import (
    JobSeekerTrackerService,
)


def _get_profile(user) -> JobSeekerProfile | None:
    return JobSeekerProfile.objects.filter(user=user, is_deleted=False).first()


class JobSeekerTrackerAPIView(LoginRequiredMixin, View):
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

        ctx = JobSeekerTrackerService().build(
            profile,
            q=(request.GET.get("q") or "").strip(),
            status=(request.GET.get("status") or "").strip(),
            company=(request.GET.get("company") or "").strip(),
            activity_page=max(1, int(request.GET.get("page") or 1)),
        )
        return JsonResponse({"success": True, "data": _serialize(ctx)})


class JobSeekerTrackerExportView(LoginRequiredMixin, View):
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

        fmt = (request.GET.get("format") or "csv").lower()
        service = JobSeekerTrackerService()
        if fmt == "csv":
            content = service.export_csv(profile)
            response = HttpResponse(content, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="career-tracker-history.csv"'
            )
            return response
        return JsonResponse(
            {"success": False, "error": "Unsupported format."}, status=400
        )


def _serialize(ctx) -> dict:
    return {
        "summary": [
            {
                "key": c.key,
                "label": c.label,
                "value": c.value,
                "raw_value": c.raw_value,
                "icon": c.icon,
                "tone": c.tone,
            }
            for c in ctx.summary
        ],
        "activities": [
            {
                "id": a.id,
                "icon": a.icon,
                "tone": a.tone,
                "title": a.title,
                "subtitle": a.subtitle,
                "company": a.company,
                "job_title": a.job_title,
                "status_label": a.status_label,
                "recruiter_name": a.recruiter_name,
                "occurred_date": a.occurred_date,
                "occurred_time": a.occurred_time,
                "detail_url": a.detail_url,
            }
            for a in ctx.activities
        ],
        "profile_analytics": ctx.profile_analytics,
        "application_charts": {
            "by_status": [
                {"label": b.label, "value": b.value, "pct": b.pct}
                for b in ctx.application_charts["by_status"]
            ],
            "interview_success_rate": ctx.application_charts["interview_success_rate"],
            "offer_conversion_rate": ctx.application_charts["offer_conversion_rate"],
        },
        "match_score": ctx.match_score,
        "updated_at": ctx.updated_at,
    }
