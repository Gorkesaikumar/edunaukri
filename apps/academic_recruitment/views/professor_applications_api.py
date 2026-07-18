"""Professor application portal JSON API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_application_portal_service import (
    ProfessorApplicationPortalService,
)

from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)


def _profile(user) -> ProfessorProfile | None:
    if not isinstance(user, ProfessorUser):
        return None
    return ProfessorProfile.objects.filter(user=user, is_deleted=False).first()


class ProfessorApplicationsAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        page = max(1, int(request.GET.get("page") or 1))
        result = ProfessorApplicationPortalService().list_applications(
            profile,
            page=page,
            status=(request.GET.get("status") or "").strip(),
            q=(request.GET.get("q") or "").strip(),
            active_only=request.GET.get("active") == "1",
            interview_only=request.GET.get("interview") == "1",
            offer_only=request.GET.get("offer") == "1",
            rejected_only=request.GET.get("rejected") == "1",
        )
        return JsonResponse({"success": True, "data": _serialize_list(result)})


@method_decorator(csrf_protect, name="dispatch")
class ProfessorApplicationOfferAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["post"]

    def post(self, request, application_id, **kwargs):
        profile = _profile(request.user)
        if not profile:
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)

        action = (request.POST.get("action") or "").strip().lower()
        if action not in {"accept", "decline"}:
            return JsonResponse(
                {"success": False, "error": "Invalid action."}, status=400
            )

        app = (
            FacultyApplicationSelector()
            .for_professor(profile)
            .filter(pk=application_id)
            .first()
        )
        if not app:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        if not ProfessorApplicationPortalService.can_respond_to_offer(app):
            return JsonResponse(
                {"success": False, "error": "No pending offer to respond to."},
                status=400,
            )

        new_status = (
            FacultyApplicationStatus.OFFER_ACCEPTED
            if action == "accept"
            else FacultyApplicationStatus.OFFER_DECLINED
        )
        try:
            FacultyApplicationService().update_status_for_actor(
                app,
                new_status,
                "Offer accepted by candidate."
                if action == "accept"
                else "Offer declined by candidate.",
                actor=request.user,
            )
            message = (
                "Offer accepted successfully."
                if action == "accept"
                else "Offer declined."
            )
            return JsonResponse({"success": True, "message": message})
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _serialize_list(result) -> dict:
    return {
        "applications": [
            {
                "id": card.id,
                "job_title": card.job_title,
                "institution_name": card.institution_name,
                "location": card.location,
                "logo_url": card.logo_url,
                "status_label": card.status_label,
                "status_class": card.status_class,
                "applied_date": card.applied_date,
                "last_updated": card.last_updated,
                "detail_url": card.detail_url,
                "job_url": card.job_url,
                "is_active": card.is_active,
            }
            for card in result.applications
        ],
        "analytics": [
            {
                "key": a.key,
                "label": a.label,
                "value": a.value,
                "icon": a.icon,
                "tone": a.tone,
            }
            for a in result.analytics
        ],
        "filters": result.filters,
        "page": result.page,
        "total_pages": result.total_pages,
        "total_count": result.total_count,
    }
