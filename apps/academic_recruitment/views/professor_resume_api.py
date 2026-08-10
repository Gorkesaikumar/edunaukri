"""Resume portal JSON API for faculty."""

from __future__ import annotations

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_resume_portal_service import (
    ProfessorResumePortalService,
)

logger = logging.getLogger(__name__)


def _get_profile(user) -> ProfessorProfile | None:
    return (
        ProfessorProfile.objects.filter(user=user, is_deleted=False)
        .select_related("cv_file")
        .first()
    )


@method_decorator(csrf_protect, name="dispatch")
class ProfessorResumePortalAPIView(LoginRequiredMixin, View):
    login_url = "/academic/login/"

    def get(self, request, *args, **kwargs):
        if not isinstance(request.user, ProfessorUser):
            return JsonResponse(
                {"success": False, "message": "Permission denied.", "errors": {"detail": "Forbidden."}},
                status=403,
            )
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "message": "Profile not found.", "errors": {"detail": "Profile not found."}},
                status=404,
            )
        try:
            page = ProfessorResumePortalService().build(profile)
            return JsonResponse(
                {
                    "success": True,
                    "data": {
                        "has_resume": page.has_resume,
                        "match_score": page.match_score,
                        "match_explanation": page.match_explanation,
                        "analytics": page.analytics,
                        "parsed": page.parsed,
                        "version": page.version,
                        "trust_report": page.trust_report,
                        "match_diagnostics": page.match_diagnostics,
                    },
                }
            )
        except Exception as exc:
            logger.exception("Error loading academic resume portal API data for user_id=%s: %s", request.user.pk, exc)
            return JsonResponse(
                {"success": False, "message": "Unable to fetch resume data.", "errors": {"detail": str(exc)}},
                status=500,
            )
