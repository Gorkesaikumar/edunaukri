"""Professor career tracker API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_tracker_portal_service import (
    ProfessorTrackerPortalService,
)


def _get_profile(user) -> ProfessorProfile | None:
    return ProfessorProfile.objects.filter(user=user, is_deleted=False).first()


class ProfessorTrackerAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        if not isinstance(request.user, ProfessorUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        ctx = ProfessorTrackerPortalService().build(
            profile,
            q=(request.GET.get("q") or "").strip(),
            status=(request.GET.get("status") or "").strip(),
            company=(request.GET.get("company") or "").strip(),
            activity_page=max(1, int(request.GET.get("page") or 1)),
        )
        return JsonResponse({"success": True, "data": _serialize(ctx)})


class ProfessorTrackerExportView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        if not isinstance(request.user, ProfessorUser):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        fmt = (request.GET.get("format") or "csv").lower()
        if fmt == "csv":
            content = ProfessorTrackerPortalService().export_csv(profile)
            response = HttpResponse(content, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="faculty-career-tracker.csv"'
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
        "pipelines": [
            {
                "application_id": p.application_id,
                "job_title": p.job_title,
                "company_name": p.company_name,
                "logo_url": p.logo_url,
                "department": p.department,
                "applied_date": p.applied_date,
                "status": p.status,
                "status_label": p.status_label,
                "status_tone": p.status_tone,
                "detail_url": p.detail_url,
                "job_url": p.job_url,
                "interview_url": p.interview_url,
                "withdraw_url": p.withdraw_url,
                "can_withdraw": p.can_withdraw,
                "offer_letter_url": p.offer_letter_url,
                "contact_email": p.contact_email,
                "recruiter_name": p.recruiter_name,
                "expected_next_step": p.expected_next_step,
                "stages": [
                    {
                        "key": s.key,
                        "label": s.label,
                        "state": s.state,
                        "state_label": s.state_label,
                        "icon": s.icon,
                        "timestamp": s.timestamp,
                        "recruiter_name": s.recruiter_name,
                        "description": s.description,
                    }
                    for s in p.stages
                ],
                "history": [
                    {
                        "date": h.date,
                        "time": h.time,
                        "status_label": h.status_label,
                        "updated_by": h.updated_by,
                        "remarks": h.remarks,
                    }
                    for h in p.history
                ],
            }
            for p in ctx.pipelines
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
