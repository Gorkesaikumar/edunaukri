"""JSON API endpoints for the job seeker profile page."""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.core.exceptions.domain_exceptions import (
    DomainException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.services.jobseeker_profile_manage_service import (
    JobSeekerProfileManageService,
)


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


class _JobSeekerProfileAPIMixin(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["get", "post", "patch", "delete"]

    def dispatch(self, request, *args, **kwargs):
        kwargs.pop("user_uuid", None)
        return super().dispatch(request, *args, **kwargs)

    def _service(self) -> JobSeekerProfileManageService:
        return JobSeekerProfileManageService()

    def _authorize(self, request):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
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
class JobSeekerProfileAPIView(_JobSeekerProfileAPIMixin):
    """Full profile read for the authenticated job seeker."""

    def get(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        data = self._service().serialize_profile(profile)
        return JsonResponse({"success": True, "data": data})


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileSectionAPIView(_JobSeekerProfileAPIMixin):
    """Update a named profile section (basic, summary, skills, career, social, header)."""

    def patch(self, request, section: str):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            data = self._service().update_section(
                profile, section, payload, actor_id=request.user.pk
            )
            if section == "career":
                from apps.it_recruitment.services.job_recommendation_engine_service import (
                    JobRecommendationEngineService,
                )

                summary = JobRecommendationEngineService().get_recommendations(
                    profile,
                    force_rebuild=False,
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
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                "Profile section save failed: %s", section
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Unable to save your profile. Please try again.",
                },
                status=500,
            )


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileExperiencesAPIView(_JobSeekerProfileAPIMixin):
    def get(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        items = [
            self._service()._serialize_experience(e)
            for e in profile.experiences.filter(is_deleted=False)
        ]
        return JsonResponse({"success": True, "data": items})

    def post(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().create_experience(
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
class JobSeekerProfileExperienceDetailAPIView(_JobSeekerProfileAPIMixin):
    def patch(self, request, experience_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().update_experience(
                profile, experience_id, payload, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": item})
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)

    def delete(self, request, experience_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            self._service().delete_experience(
                profile, experience_id, actor_id=request.user.pk
            )
            return JsonResponse({"success": True})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileEducationAPIView(_JobSeekerProfileAPIMixin):
    def post(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().create_education(
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
class JobSeekerProfileEducationDetailAPIView(_JobSeekerProfileAPIMixin):
    def patch(self, request, education_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().update_education(
                profile, education_id, payload, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": item})
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)

    def delete(self, request, education_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            self._service().delete_education(
                profile, education_id, actor_id=request.user.pk
            )
            return JsonResponse({"success": True})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileProjectsAPIView(_JobSeekerProfileAPIMixin):
    def post(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().create_project(
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
class JobSeekerProfileProjectDetailAPIView(_JobSeekerProfileAPIMixin):
    def patch(self, request, project_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().update_project(
                profile, project_id, payload, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": item})
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)

    def delete(self, request, project_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            self._service().delete_project(
                profile, project_id, actor_id=request.user.pk
            )
            return JsonResponse({"success": True})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileCertificationsAPIView(_JobSeekerProfileAPIMixin):
    def post(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().create_certification(
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
class JobSeekerProfileCertificationDetailAPIView(_JobSeekerProfileAPIMixin):
    def patch(self, request, certification_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            payload = self._parse_json(request)
            item = self._service().update_certification(
                profile, certification_id, payload, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": item})
        except (
            json.JSONDecodeError,
            ValidationException,
            ResourceNotFoundException,
            DomainException,
        ) as exc:
            return _error_response(exc)

    def delete(self, request, certification_id):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            self._service().delete_certification(
                profile, certification_id, actor_id=request.user.pk
            )
            return JsonResponse({"success": True})
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerProfileResumeAPIView(_JobSeekerProfileAPIMixin):
    def post(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        uploaded = request.FILES.get("file") or request.FILES.get("resume")
        if not uploaded:
            return JsonResponse(
                {"success": False, "error": "Resume file is required."}, status=400
            )
        try:
            data = self._service().upload_resume(
                profile, uploaded, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": data})
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse({"success": False, "error": message}, status=400)
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)
        except Exception:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Unable to upload your resume. Please try again.",
                },
                status=500,
            )

    def delete(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        data = self._service().delete_resume(profile, actor_id=request.user.pk)
        return JsonResponse({"success": True, "data": data})


class JobSeekerProfileResumeDownloadView(_JobSeekerProfileAPIMixin):
    """Download the authenticated seeker's resume."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            stored = self._service().get_resume_file(profile)
            path = StorageService().get_absolute_path(stored)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=stored.original_filename
            )
        except (ResourceNotFoundException, FileNotFoundError, DomainException) as exc:
            return _error_response(exc)


class JobSeekerProfileResumePreviewView(_JobSeekerProfileAPIMixin):
    """Inline preview for PDF resumes."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        try:
            stored = self._service().get_resume_file(profile)
            ext = (
                stored.original_filename.rsplit(".", 1)[-1].lower()
                if stored.original_filename
                else ""
            )
            if ext != "pdf":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Preview is available for PDF resumes only.",
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
class JobSeekerProfilePhotoAPIView(_JobSeekerProfileAPIMixin):
    def post(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        uploaded = request.FILES.get("file") or request.FILES.get("photo")
        if not uploaded:
            return JsonResponse(
                {"success": False, "error": "Photo file is required."}, status=400
            )
        try:
            data = self._service().upload_photo(
                profile, uploaded, actor_id=request.user.pk
            )
            return JsonResponse({"success": True, "data": data})
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse({"success": False, "error": message}, status=400)
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)
        except Exception as exc:
            import logging
            import traceback
            with open("d:\\edunaukri\\error.log", "w") as f:
                f.write(traceback.format_exc())
            logging.getLogger(__name__).exception("Profile photo upload failed")
            return JsonResponse(
                {
                    "success": False,
                    "error": "Unable to upload your photo. Please try again.",
                },
                status=500,
            )

    def delete(self, request, *args, **kwargs):
        profile = self._authorize(request)
        if profile is None:
            return _forbidden()
        data = self._service().delete_photo(profile, actor_id=request.user.pk)
        return JsonResponse({"success": True, "data": data})
