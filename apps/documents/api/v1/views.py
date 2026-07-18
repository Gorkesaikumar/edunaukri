from drf_spectacular.utils import extend_schema

from django.http import FileResponse
from rest_framework import permissions, status
from apps.authentication.permissions.throttles import BruteForceIPThrottle, ResumeUploadThrottle

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.core.constants.enums import DomainType
from apps.core.views.base import EnvelopeAPIView
from apps.documents.api.v1.serializers import FileUploadSerializer, StoredFileSerializer
from apps.documents.selectors.stored_file_selector import StoredFileSelector
from apps.documents.services.file_access_service import FileAccessService
from apps.documents.services.storage_service import StorageService


def _domain_for_user(user) -> str:
    if isinstance(user, ITUser):
        return DomainType.IT
    if isinstance(user, (ProfessorUser, CollegeUser)):
        return DomainType.FACULTY
    if isinstance(user, AdminUser):
        return DomainType.PLATFORM
    return DomainType.PLATFORM


class FileUploadView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [BruteForceIPThrottle, ResumeUploadThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        FileAccessService().assert_can_upload(
            user=request.user, owner_id=data["owner_id"]
        )

        stored = StorageService().upload(
            uploaded_file=data["file"],
            domain=_domain_for_user(request.user),
            file_type=data["file_type"],
            owner_type=data["owner_type"],
            owner_id=data["owner_id"],
            uploaded_by_id=request.user.pk,
        )
        return self.success_response(
            StoredFileSerializer(stored).data, status=status.HTTP_201_CREATED
        )


class FileDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ResumeUploadThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, file_id):
        stored = StoredFileSelector().get_active(file_id)
        if not stored:
            return self.error_response("NOT_FOUND", "File not found.", status=404)
        FileAccessService().assert_can_access(user=request.user, stored_file=stored)
        return self.success_response(StoredFileSerializer(stored).data)


class FileDownloadView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ResumeUploadThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, file_id):
        stored = StoredFileSelector().get_active(file_id)
        if not stored:
            return self.error_response("NOT_FOUND", "File not found.", status=404)
        FileAccessService().assert_can_access(user=request.user, stored_file=stored)

        path = StorageService().get_absolute_path(stored)
        if not path.exists():
            return self.error_response(
                "NOT_FOUND", "File missing from storage.", status=404
            )

        return FileResponse(
            path.open("rb"), as_attachment=True, filename=stored.original_filename
        )
