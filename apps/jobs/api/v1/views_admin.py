from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.jobs.api.schema import (
    admin_job_dashboard_schema,
    admin_job_detail_schema,
    admin_job_list_schema,
    admin_job_reject_schema,
)
from apps.jobs.api.v1.serializers import JobModerationSerializer, JobPostingSerializer
from apps.jobs.selectors.job_selector import JobPostingSelector
from apps.jobs.services.job_publication_service import JobPublicationService
from apps.jobs.services.job_statistics_service import JobStatisticsService


class _AdminJobView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    def _job_or_error(self, job_id):
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return None, self.error_response("NOT_FOUND", "Job not found.", status=404)
        return job, None


class AdminJobListView(_AdminJobView):
    @admin_job_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        jobs = JobPostingSelector().admin_list(
            status=request.query_params.get("status"),
            company_id=request.query_params.get("company_id"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)


class AdminJobDetailView(_AdminJobView):
    @admin_job_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job, error = self._job_or_error(job_id)
        if error:
            return error
        return self.success_response(JobPostingSerializer(job).data)


class AdminJobRejectView(_AdminJobView):
    @admin_job_reject_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        job, error = self._job_or_error(job_id)
        if error:
            return error
        serializer = JobModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = JobPublicationService().admin_reject(
            job_posting=job,
            admin_id=request.user.pk,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return self.success_response(JobPostingSerializer(job).data)


class AdminJobDashboardView(_AdminJobView):
    @admin_job_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(JobStatisticsService().platform_dashboard())
