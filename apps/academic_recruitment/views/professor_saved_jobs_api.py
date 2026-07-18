"""Saved faculty vacancies JSON API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.faculty.services.saved_vacancy_service import SavedVacancyService


def _get_profile(user) -> ProfessorProfile | None:
    if not isinstance(user, ProfessorUser):
        return None
    return ProfessorProfile.objects.filter(user=user, is_deleted=False).first()


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


class ProfessorSavedVacanciesAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return _forbidden()
        page = max(1, int(request.GET.get("page") or 1))
        result = SavedVacancyService().list_saved(profile, page=page)
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "vacancies": [v.to_dict() for v in result.vacancies],
                    "total_count": result.total_count,
                    "page": result.page,
                    "page_size": result.page_size,
                    "total_pages": result.total_pages,
                },
                "saved_count": result.total_count,
            }
        )


class ProfessorSavedVacancyStatusAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return _forbidden()
        raw = request.GET.get("ids") or ""
        vacancy_ids = [part.strip() for part in raw.split(",") if part.strip()]
        status = SavedVacancyService().status_map(profile, vacancy_ids)
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "status": status,
                    "saved_count": SavedVacancyService().count(profile),
                },
            }
        )
