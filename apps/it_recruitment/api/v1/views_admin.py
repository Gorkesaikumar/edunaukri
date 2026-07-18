from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.companies.selectors.company_selector import CompanySelector
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.it_recruitment.api.v1.serializers import (
    CompanySerializer,
    JobPostingSerializer,
)
from apps.jobs.selectors.job_selector import JobPostingSelector
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

AdminEnvelope = inline_serializer(
    name="AdminJobEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

admin_job_list_schema = extend_schema(
    tags=["admin-recruitment"],
    summary="Admin: list all job postings",
    responses={200: AdminEnvelope},
)

admin_company_list_schema = extend_schema(
    tags=["admin-recruitment"],
    summary="Admin: list all companies",
    responses={200: AdminEnvelope},
)


class AdminCompanyListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @admin_company_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        companies = CompanySelector().admin_list(
            search=request.query_params.get("search")
        )
        return paginate_envelope(request, companies, CompanySerializer)


class AdminJobPostingListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @admin_job_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        jobs = JobPostingSelector().admin_list(
            status=request.query_params.get("status"),
            company_id=request.query_params.get("company_id"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)
