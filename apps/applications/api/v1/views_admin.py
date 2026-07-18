from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.applications.api.schema import (
    application_detail_schema,
    application_history_schema,
    application_status_schema,
)
from apps.applications.api.v1.serializers import (
    FacultyApplicationSerializer,
    FacultyApplicationStatusHistorySerializer,
    FacultyApplicationStatusSerializer,
    JobApplicationSerializer,
    JobApplicationStatusHistorySerializer,
    JobApplicationStatusSerializer,
    AdminJobApplicationSerializer,
    AdminFacultyApplicationSerializer,
)
from apps.applications.selectors.application_selector import (
    FacultyApplicationSelector,
    JobApplicationSelector,
)
from apps.applications.selectors.status_history_selector import (
    FacultyApplicationStatusHistorySelector,
    JobApplicationStatusHistorySelector,
)
from apps.applications.services.application_service import JobApplicationService
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

AdminEnvelope = inline_serializer(
    name="AdminApplicationEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

admin_it_application_list_schema = extend_schema(
    tags=["admin-recruitment"],
    summary="Admin: list IT job applications",
    responses={200: AdminEnvelope},
)

admin_faculty_application_list_schema = extend_schema(
    tags=["admin-recruitment"],
    summary="Admin: list faculty applications",
    responses={200: AdminEnvelope},
)


class AdminJobApplicationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @admin_it_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        queryset = JobApplicationSelector().admin_list(
            status=request.query_params.get("status"),
            job_posting_id=request.query_params.get("job_posting_id"),
        )
        return paginate_envelope(request, queryset, AdminJobApplicationSerializer)


class AdminJobApplicationDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @application_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        return self.success_response(AdminJobApplicationSerializer(application).data)


class AdminJobApplicationStatusView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @application_status_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        serializer = JobApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        application = JobApplicationService().update_status_for_actor(
            application,
            serializer.validated_data["status"],
            serializer.validated_data.get("notes", ""),
            actor=request.user,
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        return self.success_response(AdminJobApplicationSerializer(application).data)


class AdminJobApplicationHistoryView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @application_history_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        history = JobApplicationStatusHistorySelector().for_application(application)
        return self.success_response(
            JobApplicationStatusHistorySerializer(history, many=True).data
        )


class AdminFacultyApplicationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @admin_faculty_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        queryset = FacultyApplicationSelector().admin_list(
            status=request.query_params.get("status"),
            vacancy_id=request.query_params.get("vacancy_id"),
        )
        return paginate_envelope(request, queryset, AdminFacultyApplicationSerializer)


class AdminFacultyApplicationDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @extend_schema(
        tags=["admin-recruitment"],
        summary="Admin: faculty application detail",
        responses={200: AdminEnvelope},
    )
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        return self.success_response(
            AdminFacultyApplicationSerializer(application).data
        )


class AdminFacultyApplicationStatusView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @extend_schema(
        tags=["admin-recruitment"],
        summary="Admin: update faculty application status",
        responses={200: AdminEnvelope},
    )
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        serializer = FacultyApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        application = FacultyApplicationService().update_status_for_actor(
            application,
            serializer.validated_data["status"],
            serializer.validated_data.get("notes", ""),
            actor=request.user,
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        return self.success_response(
            AdminFacultyApplicationSerializer(application).data
        )


class AdminFacultyApplicationHistoryView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @extend_schema(
        tags=["admin-recruitment"],
        summary="Admin: faculty application history",
        responses={200: AdminEnvelope},
    )
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        history = FacultyApplicationStatusHistorySelector().for_application(application)
        return self.success_response(
            FacultyApplicationStatusHistorySerializer(history, many=True).data
        )
