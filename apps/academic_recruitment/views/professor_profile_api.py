"""JSON API endpoints for the professor profile page."""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.services.professor_profile_manage_service import (
    ProfessorProfileManageService,
)
from apps.core.exceptions.domain_exceptions import (
    DomainException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.documents.services.storage_service import StorageService


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _error_response(exc: Exception):
    if isinstance(exc, ValidationException):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    if isinstance(exc, ResourceNotFoundException):
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
    if isinstance(exc, DomainException):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse(
        {"success": False, "error": "Something went wrong."}, status=500
    )


class _ProfessorProfileAPIMixin(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["get", "post", "patch"]

    def _service(self) -> ProfessorProfileManageService:
        return ProfessorProfileManageService()

    def _authorize(self, request):
        if not isinstance(request.user, ProfessorUser):
            return None
        try:
            return self._service().get_profile_for_user(request.user)
        except ResourceNotFoundException:
            return None

    def _parse_json(self, request) -> dict:
        if request.content_type and "application/json" in request.content_type:
            if not request.body:
                return {}
            return json.loads(request.body.decode("utf-8"))
        return request.POST.dict()


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfileAPIView(_ProfessorProfileAPIMixin):
    def get(self, request, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        return JsonResponse(
            {"success": True, "data": self._service().serialize_profile(profile)}
        )


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfileSectionAPIView(_ProfessorProfileAPIMixin):
    def patch(self, request, section: str, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            data = self._service().update_section(
                profile, section, payload, actor_id=request.user.pk
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Profile updated successfully.",
                    "data": data,
                    "profile": data,
                }
            )
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfilePhotoAPIView(_ProfessorProfileAPIMixin):
    def post(self, request, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        uploaded = request.FILES.get("photo") or request.FILES.get("file")
        if not uploaded:
            return JsonResponse(
                {"success": False, "error": "Photo file is required."}, status=400
            )
        try:
            data = self._service().upload_photo(
                profile, uploaded, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": data})
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfileCVAPIView(_ProfessorProfileAPIMixin):
    def post(self, request, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        uploaded = request.FILES.get("cv") or request.FILES.get("file")
        if not uploaded:
            return JsonResponse(
                {"success": False, "error": "CV file is required."}, status=400
            )
        try:
            data = self._service().upload_cv(
                profile, uploaded, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": data})
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)

    def delete(self, request, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        data = self._service().delete_cv(profile, actor_id=request.user.pk)
        return JsonResponse({"success": True, "data": data})


class ProfessorProfileCVDownloadView(_ProfessorProfileAPIMixin):
    http_method_names = ["get"]

    def get(self, request, **kwargs):
        from django.http import FileResponse

        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            stored = self._service().get_cv_file(profile)
            path = StorageService().get_absolute_path(stored)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=stored.original_filename
            )
        except (ResourceNotFoundException, FileNotFoundError, DomainException) as exc:
            return _error_response(exc)


class ProfessorProfileCVPreviewView(_ProfessorProfileAPIMixin):
    http_method_names = ["get"]

    def get(self, request, **kwargs):
        from django.http import FileResponse

        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            stored = self._service().get_cv_file(profile)
            ext = (
                stored.original_filename.rsplit(".", 1)[-1].lower()
                if stored.original_filename
                else ""
            )
            if ext != "pdf":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Preview is available for PDF files only.",
                    },
                    status=400,
                )
            path = StorageService().get_absolute_path(stored)
            response = FileResponse(
                path.open("rb"), as_attachment=False, filename=stored.original_filename
            )
            response["Content-Type"] = "application/pdf"
            return response
        except (ResourceNotFoundException, FileNotFoundError, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfileQualificationsAPIView(_ProfessorProfileAPIMixin):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().create_qualification(
                profile, payload, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": item}, status=201)
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorProfileQualificationDetailAPIView(_ProfessorProfileAPIMixin):
    http_method_names = ["patch", "delete"]

    def patch(self, request, qualification_id, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().update_qualification(
                profile, qualification_id, payload, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": item})
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)

    def delete(self, request, qualification_id, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            self._service().delete_qualification(
                profile, qualification_id, actor_id=request.user.pk
            )
            return JsonResponse({"success": True})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)
