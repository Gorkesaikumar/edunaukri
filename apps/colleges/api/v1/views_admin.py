from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.colleges.api.schema import (
    admin_institution_dashboard_schema,
    admin_institution_detail_schema,
    admin_institution_list_schema,
    admin_institution_verify_schema,
)
from apps.colleges.api.v1.serializers import InstitutionSerializer
from apps.colleges.selectors.college_selector import CollegeSelector
from apps.colleges.services.institution_statistics_service import (
    InstitutionStatisticsService,
)
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView


class _AdminInstitutionView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    def _institution_or_error(self, college_id):
        institution = CollegeSelector().get_or_none(college_id)
        if not institution:
            return None, self.error_response(
                "NOT_FOUND", "Institution not found.", status=404
            )
        return institution, None


class AdminInstitutionListView(_AdminInstitutionView):
    @admin_institution_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("1", "true", "yes")
        institutions = CollegeSelector().admin_list(
            is_active=is_active,
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, institutions, InstitutionSerializer)


class AdminInstitutionDetailView(_AdminInstitutionView):
    @admin_institution_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        return self.success_response(InstitutionSerializer(institution).data)


class AdminInstitutionVerifyView(_AdminInstitutionView):
    @admin_institution_verify_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        from apps.colleges.api.v1.serializers import InstitutionVerificationSerializer

        serializer = InstitutionVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                "VALIDATION_ERROR", serializer.errors, status=400
            )
        from apps.core.constants.enums import ProfileStatusEnum

        institution.verification_status = ProfileStatusEnum.VERIFIED.value
        institution.verification_remarks = serializer.validated_data.get("remarks", "")
        from django.utils import timezone

        institution.verified_at = timezone.now()
        institution.save(
            update_fields=["verification_status", "verification_remarks", "verified_at"]
        )
        return self.success_response(InstitutionSerializer(institution).data)


class AdminInstitutionDashboardView(_AdminInstitutionView):
    @admin_institution_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(
            InstitutionStatisticsService().platform_dashboard()
        )
