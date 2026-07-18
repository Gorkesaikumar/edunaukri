from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.companies.api.schema import (
    company_activate_schema,
    company_branding_schema,
    company_create_schema,
    company_dashboard_schema,
    company_deactivate_schema,
    company_delete_schema,
    company_detail_schema,
    company_list_schema,
    company_location_create_schema,
    company_location_detail_schema,
    company_location_list_schema,
    company_member_add_schema,
    company_member_list_schema,
    company_member_remove_schema,
    company_update_schema,
)
from apps.companies.api.v1.serializers import (
    CompanyBrandingSerializer,
    CompanyCreateSerializer,
    CompanyLocationSerializer,
    CompanyLocationWriteSerializer,
    CompanyMemberAddSerializer,
    CompanyMemberSerializer,
    CompanySerializer,
    CompanyUpdateSerializer,
)
from apps.companies.permissions.company_permissions import (
    IsCompanyMember,
    IsCompanyOwner,
)
from apps.companies.selectors.company_selector import (
    CompanyLocationSelector,
    CompanyMemberSelector,
    CompanySelector,
)
from apps.companies.services.company_branding_service import CompanyBrandingService
from apps.companies.services.company_location_service import CompanyLocationService
from apps.companies.services.company_member_service import CompanyMemberService
from apps.companies.services.company_service import CompanyService
from apps.companies.services.company_statistics_service import CompanyStatisticsService
from apps.core.pagination import paginate_envelope
from apps.core.permissions.roles import IsRecruiter
from apps.core.views.base import EnvelopeAPIView
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector


class _RecruiterCompanyView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    def _recruiter_or_error(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return None, self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        return recruiter, None

    def _company_or_error(self, company_id):
        company = CompanySelector().get_or_none(company_id)
        if not company:
            return None, self.error_response(
                "NOT_FOUND", "Company not found.", status=404
            )
        return company, None


class CompanyListCreateView(_RecruiterCompanyView):
    @company_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        companies = CompanySelector().for_recruiter(recruiter)
        return paginate_envelope(request, companies, CompanySerializer)

    @company_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        serializer = CompanyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = CompanyService().create_company(
            recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(
            CompanySerializer(company).data, status=status.HTTP_201_CREATED
        )


class CompanyDetailView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        company, error = self._company_or_error(company_id)
        if error:
            return error
        return self.success_response(CompanySerializer(company).data)

    @company_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        serializer = CompanyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        company = CompanyService().update_company(
            company=company, recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(CompanySerializer(company).data)

    @company_delete_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        CompanyService().soft_delete(company=company, recruiter=recruiter)
        return self.success_response({"deleted": True})


class CompanyActivateView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_activate_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        company = CompanyService().activate(company=company, recruiter=recruiter)
        return self.success_response(CompanySerializer(company).data)


class CompanyDeactivateView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_deactivate_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        company = CompanyService().deactivate(company=company, recruiter=recruiter)
        return self.success_response(CompanySerializer(company).data)


class CompanyBrandingView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_branding_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        serializer = CompanyBrandingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = CompanyBrandingService()
        if serializer.validated_data.get("logo_file_id"):
            company = service.set_logo(
                company=company,
                recruiter=recruiter,
                user=request.user,
                logo_file_id=serializer.validated_data["logo_file_id"],
            )
        if serializer.validated_data.get("banner_file_id"):
            company = service.set_banner(
                company=company,
                recruiter=recruiter,
                user=request.user,
                banner_file_id=serializer.validated_data["banner_file_id"],
            )
        return self.success_response(CompanySerializer(company).data)


class CompanyDashboardView(_RecruiterCompanyView):
    @company_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        summary = CompanyStatisticsService().recruiter_dashboard(recruiter)
        return self.success_response(summary)


class CompanyLocationListCreateView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_location_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        company, error = self._company_or_error(company_id)
        if error:
            return error
        locations = CompanyLocationSelector().for_company(company_id)
        return self.success_response(
            CompanyLocationSerializer(locations, many=True).data
        )

    @company_location_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        serializer = CompanyLocationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = CompanyLocationService().add_location(
            company=company, recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(
            CompanyLocationSerializer(location).data, status=status.HTTP_201_CREATED
        )


class CompanyLocationDetailView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_location_detail_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, company_id, location_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        serializer = CompanyLocationWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        location = CompanyLocationService().update_location(
            company=company,
            recruiter=recruiter,
            location_id=location_id,
            data=serializer.validated_data,
        )
        return self.success_response(CompanyLocationSerializer(location).data)

    @company_location_detail_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, company_id, location_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        CompanyLocationService().delete_location(
            company=company, recruiter=recruiter, location_id=location_id
        )
        return self.success_response({"deleted": True})


class CompanyMemberListView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyMember]

    @company_member_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        company, error = self._company_or_error(company_id)
        if error:
            return error
        members = CompanyMemberSelector().for_company(company_id)
        return self.success_response(CompanyMemberSerializer(members, many=True).data)

    @company_member_add_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        serializer = CompanyMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = CompanyMemberService().add_member(
            company=company,
            actor=recruiter,
            recruiter_email=serializer.validated_data["recruiter_email"],
            role=serializer.validated_data["role"],
        )
        return self.success_response(
            CompanyMemberSerializer(member).data, status=status.HTTP_201_CREATED
        )


class CompanyMemberDetailView(_RecruiterCompanyView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsCompanyOwner]

    @company_member_remove_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, company_id, member_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        company, error = self._company_or_error(company_id)
        if error:
            return error
        CompanyMemberService().remove_member(
            company=company, actor=recruiter, member_id=member_id
        )
        return self.success_response({"removed": True})
