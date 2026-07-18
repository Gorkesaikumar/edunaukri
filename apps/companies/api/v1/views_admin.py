from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.companies.api.schema import (
    admin_company_dashboard_schema,
    admin_company_detail_schema,
    admin_company_list_schema,
    admin_company_verify_schema,
)
from apps.companies.api.v1.serializers import CompanySerializer
from apps.companies.selectors.company_selector import CompanySelector
from apps.companies.services.company_statistics_service import CompanyStatisticsService
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView


class _AdminCompanyView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    def _company_or_error(self, company_id):
        company = CompanySelector().get_or_none(company_id)
        if not company:
            return None, self.error_response(
                "NOT_FOUND", "Company not found.", status=404
            )
        return company, None


class AdminCompanyListView(_AdminCompanyView):
    @admin_company_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            is_active = is_active.lower() in ("1", "true", "yes")
        companies = CompanySelector().admin_list(
            is_active=is_active,
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, companies, CompanySerializer)


class AdminCompanyDetailView(_AdminCompanyView):
    @admin_company_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        company, error = self._company_or_error(company_id)
        if error:
            return error
        return self.success_response(CompanySerializer(company).data)


class AdminCompanyVerifyView(_AdminCompanyView):
    @admin_company_verify_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id):
        company, error = self._company_or_error(company_id)
        if error:
            return error
        from apps.companies.api.v1.serializers import CompanyVerificationSerializer

        serializer = CompanyVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                "VALIDATION_ERROR", serializer.errors, status=400
            )
        from apps.core.constants.enums import ProfileStatusEnum

        company.verification_status = ProfileStatusEnum.VERIFIED.value
        company.verification_remarks = serializer.validated_data.get("remarks", "")
        from django.utils import timezone

        company.verified_at = timezone.now()
        company.save(
            update_fields=["verification_status", "verification_remarks", "verified_at"]
        )
        return self.success_response(CompanySerializer(company).data)


class AdminCompanyDashboardView(_AdminCompanyView):
    @admin_company_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(CompanyStatisticsService().platform_dashboard())
