"""Certificate Management Center JSON and file endpoints for faculty job seekers."""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_certificate_management_service import (
    ProfessorCertificateManagementService,
)
from apps.academic_recruitment.services.professor_certificate_portal_service import (
    ProfessorCertificatePortalService,
)
from apps.core.exceptions.domain_exceptions import (
    DomainException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.documents.services.storage_service import StorageService


def _get_profile(user) -> ProfessorProfile | None:
    if not isinstance(user, ProfessorUser):
        return None
    return ProfessorProfile.objects.filter(user=user, is_deleted=False).first()


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _error_response(exc):
    if isinstance(exc, ResourceNotFoundException):
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
    if isinstance(exc, ValidationException):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    if isinstance(exc, DomainException):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _serialize_cert(cert) -> dict:
    mgmt = ProfessorCertificateManagementService()
    status = mgmt.resolve_status(cert)
    ext = ""
    if cert.certificate_file and cert.certificate_file.original_filename:
        parts = cert.certificate_file.original_filename.rsplit(".", 1)
        if len(parts) == 2:
            ext = parts[1].lower()
    return {
        "id": str(cert.id),
        "name": cert.name,
        "issuing_organization": cert.issuing_organization,
        "category": cert.category,
        "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
        "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
        "credential_id": cert.credential_id,
        "credential_url": cert.credential_url,
        "is_verified": cert.is_verified,
        "has_file": bool(cert.certificate_file_id),
        "file_name": cert.certificate_file.original_filename
        if cert.certificate_file
        else "",
        "file_type": ext.upper() if ext else "",
        "status_key": status.key,
        "status_label": status.label,
    }


@method_decorator(csrf_protect, name="dispatch")
class ProfessorCertificatesAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def get(self, request, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        page = ProfessorCertificatePortalService().build(
            profile,
            page=int(request.GET.get("page") or 1),
            q=(request.GET.get("q") or "").strip(),
            category=(request.GET.get("category") or "").strip(),
            status_filter=(request.GET.get("status") or "").strip(),
            organization=(request.GET.get("organization") or "").strip(),
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "total_count": page.total_count,
                    "completion_percentage": page.completion_percentage,
                    "certificates": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "organization": c.organization,
                            "category": c.category,
                            "category_label": c.category_label,
                            "issue_label": c.issue_label,
                            "expiry_label": c.expiry_label,
                            "status_key": c.status_key,
                            "status_label": c.status_label,
                            "has_file": c.has_file,
                            "preview_url": c.preview_url,
                            "download_url": c.download_url,
                            "detail_api_url": c.detail_api_url,
                        }
                        for c in page.certificates
                    ],
                },
            }
        )

    def post(self, request, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        uploaded = request.FILES.get("file") or request.FILES.get("certificate")
        data = request.POST.dict()
        if not uploaded:
            return JsonResponse(
                {"success": False, "error": "Certificate file is required."}, status=400
            )
        if not data.get("name"):
            return JsonResponse(
                {"success": False, "error": "Certificate name is required."}, status=400
            )
        try:
            cert = ProfessorCertificateManagementService().create(
                profile,
                actor_id=request.user.pk,
                data=data,
                uploaded_file=uploaded,
            )
            return JsonResponse(
                {
                    "success": True,
                    "data": _serialize_cert(cert),
                    "message": "Certificate uploaded successfully.",
                },
                status=201,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse({"success": False, "error": message}, status=400)
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class ProfessorCertificateDetailAPIView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"

    def patch(self, request, certification_id, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        try:
            if request.content_type and "application/json" in request.content_type:
                data = json.loads(request.body.decode("utf-8") or "{}")
            else:
                data = request.POST.dict()
            uploaded = request.FILES.get("file") or request.FILES.get("certificate")
            mgmt = ProfessorCertificateManagementService()
            if uploaded:
                cert = mgmt.replace_file(
                    profile,
                    certification_id,
                    actor_id=request.user.pk,
                    uploaded_file=uploaded,
                )
            else:
                cert = mgmt.update(
                    profile, certification_id, actor_id=request.user.pk, data=data
                )
            return JsonResponse(
                {
                    "success": True,
                    "data": _serialize_cert(cert),
                    "message": "Certificate updated successfully.",
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON payload."}, status=400
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return JsonResponse({"success": False, "error": message}, status=400)
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)

    def delete(self, request, certification_id, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )
        try:
            ProfessorCertificateManagementService().delete(
                profile, certification_id, actor_id=request.user.pk
            )
            return JsonResponse(
                {"success": True, "message": "Certificate deleted successfully."}
            )
        except (ValidationException, ResourceNotFoundException, DomainException) as exc:
            return _error_response(exc)


class ProfessorCertificateDownloadView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["get"]

    def get(self, request, certification_id, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        try:
            stored = ProfessorCertificateManagementService().get_file(
                profile, certification_id
            )
            path = StorageService().get_absolute_path(stored)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=stored.original_filename
            )
        except (ResourceNotFoundException, FileNotFoundError, DomainException) as exc:
            return _error_response(exc)


class ProfessorCertificatePreviewView(LoginRequiredMixin, View):
    login_url = "/faculty/login/professor/"
    http_method_names = ["get"]

    def get(self, request, certification_id, **kwargs):
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        try:
            stored = ProfessorCertificateManagementService().get_file(
                profile, certification_id
            )
            ext = (
                stored.original_filename.rsplit(".", 1)[-1].lower()
                if stored.original_filename
                else ""
            )
            path = StorageService().get_absolute_path(stored)
            if ext == "pdf":
                response = FileResponse(
                    path.open("rb"),
                    as_attachment=False,
                    filename=stored.original_filename,
                )
                response["Content-Type"] = "application/pdf"
                return response
            if ext in {"jpg", "jpeg", "png"}:
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}[
                    ext
                ]
                response = FileResponse(
                    path.open("rb"),
                    as_attachment=False,
                    filename=stored.original_filename,
                )
                response["Content-Type"] = mime
                return response
            return JsonResponse(
                {
                    "success": False,
                    "error": "Preview is available for PDF and image certificates only.",
                },
                status=400,
            )
        except (ResourceNotFoundException, FileNotFoundError, DomainException) as exc:
            return _error_response(exc)
