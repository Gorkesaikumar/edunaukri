from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle, BruteForceIPThrottle

from apps.core.pagination import paginate_envelope
from apps.core.permissions.roles import IsRecruiter
from apps.core.views.base import EnvelopeAPIView
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector
from apps.jobs.api.schema import (
    job_archive_schema,
    job_close_schema,
    job_company_list_schema,
    job_create_schema,
    job_dashboard_schema,
    job_delete_schema,
    job_detail_schema,
    job_duplicate_schema,
    job_list_create_list_schema,
    job_pause_schema,
    job_preview_schema,
    job_public_detail_schema,
    job_public_list_schema,
    job_publish_schema,
    job_recruiter_list_schema,
    job_reopen_schema,
    job_statistics_schema,
    job_template_list_schema,
    job_unpublish_schema,
    job_update_schema,
    job_visibility_schema,
)
from apps.jobs.api.v1.serializers import (
    JobCreateSerializer,
    JobPostingSerializer,
    JobUpdateSerializer,
    JobVisibilitySerializer,
)
from apps.jobs.permissions.job_permissions import CanManageJob
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.jobs.selectors.job_search import JobSearchSelector
from apps.jobs.selectors.job_selector import (
    CompanyJobSelector,
    JobPostingSelector,
    PublicJobSelector,
    RecruiterJobSelector,
)
from apps.jobs.services.job_lifecycle_service import JobLifecycleService
from apps.jobs.services.job_publication_service import JobPublicationService
from apps.jobs.services.job_service import JobService
from apps.jobs.services.job_statistics_service import JobStatisticsService
from apps.jobs.services.job_visibility_service import JobVisibilityService


class _RecruiterJobView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    def _recruiter_or_error(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return None, self.error_response(
                "PERMISSION_DENIED", "Recruiter profile required.", status=403
            )
        return recruiter, None

    def _job_or_error(self, job_id):
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return None, self.error_response("NOT_FOUND", "Job not found.", status=404)
        return job, None


class JobListCreateView(_RecruiterJobView):
    @job_list_create_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        jobs = RecruiterJobSelector().for_recruiter(
            recruiter, status=request.query_params.get("status")
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)

    @job_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = JobService().create_job(
            recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(
            JobPostingSerializer(job).data, status=status.HTTP_201_CREATED
        )


class RecruiterJobListView(_RecruiterJobView):
    @job_recruiter_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        jobs = RecruiterJobSelector().for_recruiter(
            recruiter, status=request.query_params.get("status")
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)


class JobTemplateListView(_RecruiterJobView):
    @job_template_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        templates = RecruiterJobSelector().templates(recruiter)
        return paginate_envelope(request, templates, JobPostingSerializer)


class JobDetailView(_RecruiterJobView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, CanManageJob]

    @job_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job, error = self._job_or_error(job_id)
        if error:
            return error
        return self.success_response(JobPostingSerializer(job).data)

    @job_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, job_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        job, error = self._job_or_error(job_id)
        if error:
            return error
        serializer = JobUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        job = JobService().update_job(
            job_posting=job, recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(JobPostingSerializer(job).data)

    @job_delete_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, job_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        job, error = self._job_or_error(job_id)
        if error:
            return error
        JobService().soft_delete(job_posting=job, recruiter=recruiter)
        return self.success_response({"deleted": True})


class JobPreviewView(_RecruiterJobView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, CanManageJob]

    @job_preview_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job, error = self._job_or_error(job_id)
        if error:
            return error
        return self.success_response(JobPostingSerializer(job).data)


class _JobActionView(_RecruiterJobView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, CanManageJob]

    def _run(self, request, job_id, handler):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        job, error = self._job_or_error(job_id)
        if error:
            return error
        job = handler(recruiter, job)
        return self.success_response(JobPostingSerializer(job).data)


class JobPublishView(_JobActionView):
    @job_publish_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        return self._run(
            request,
            job_id,
            lambda r, j: JobPublicationService().publish(job_posting=j, recruiter=r),
        )


class JobUnpublishView(_JobActionView):
    @job_unpublish_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        return self._run(
            request,
            job_id,
            lambda r, j: JobPublicationService().unpublish(job_posting=j, recruiter=r),
        )


class JobPauseView(_JobActionView):
    @job_pause_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        return self._run(
            request,
            job_id,
            lambda r, j: JobLifecycleService().pause(job_posting=j, recruiter=r),
        )


class JobReopenView(_JobActionView):
    @job_reopen_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        return self._run(
            request,
            job_id,
            lambda r, j: JobLifecycleService().reopen(job_posting=j, recruiter=r),
        )


class JobCloseView(_JobActionView):
    @job_close_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        return self._run(
            request,
            job_id,
            lambda r, j: JobLifecycleService().close(job_posting=j, recruiter=r),
        )


class JobArchiveView(_JobActionView):
    @job_archive_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        return self._run(
            request,
            job_id,
            lambda r, j: JobLifecycleService().archive(job_posting=j, recruiter=r),
        )


class JobDuplicateView(_JobActionView):
    @job_duplicate_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        job, error = self._job_or_error(job_id)
        if error:
            return error
        clone = JobService().duplicate_job(job_posting=job, recruiter=recruiter)
        return self.success_response(
            JobPostingSerializer(clone).data, status=status.HTTP_201_CREATED
        )


class JobVisibilityView(_JobActionView):
    @job_visibility_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        job, error = self._job_or_error(job_id)
        if error:
            return error
        serializer = JobVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = JobVisibilityService()
        if "is_featured" in data:
            job = service.set_featured(
                job_posting=job, recruiter=recruiter, value=data["is_featured"]
            )
        if "is_urgent" in data:
            job = service.set_urgent(
                job_posting=job, recruiter=recruiter, value=data["is_urgent"]
            )
        if "visibility" in data:
            job = service.set_visibility(
                job_posting=job, recruiter=recruiter, visibility=data["visibility"]
            )
        return self.success_response(JobPostingSerializer(job).data)


class JobStatisticsView(_RecruiterJobView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, CanManageJob]

    @job_statistics_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        job, error = self._job_or_error(job_id)
        if error:
            return error
        stats = JobStatisticsService().job_statistics(
            job_posting=job, recruiter=recruiter
        )
        return self.success_response(stats)


class JobDashboardView(_RecruiterJobView):
    @job_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        return self.success_response(
            JobStatisticsService().recruiter_dashboard(recruiter)
        )


class CompanyJobListView(_RecruiterJobView):
    @job_company_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        recruiter, error = self._recruiter_or_error(request)
        if error:
            return error
        from apps.companies.selectors.company_selector import CompanyMemberSelector

        if not CompanyMemberSelector().is_member(recruiter, company_id):
            return self.error_response(
                "PERMISSION_DENIED", "You are not a member of this company.", status=403
            )
        jobs = CompanyJobSelector().for_company(
            company_id, status=request.query_params.get("status")
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)


class PublicJobListView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle]

    @staticmethod
    def _as_int(value):
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_bool(value):
        if value is None:
            return None
        return value.lower() in ("1", "true", "yes")

    @job_public_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        params = request.query_params
        skills = params.get("skills")
        jobs = JobSearchSelector().search(
            query=params.get("q", ""),
            location=params.get("location", ""),
            employment_type=params.get("employment_type", ""),
            work_mode=params.get("work_mode", ""),
            is_remote=self._as_bool(params.get("is_remote")),
            skills=[s.strip() for s in skills.split(",") if s.strip()]
            if skills
            else None,
            experience=self._as_int(params.get("experience")),
            salary_min=params.get("salary_min") or None,
            salary_max=params.get("salary_max") or None,
            sort=params.get("sort", "recent"),
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)


class PublicJobDetailView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle]

    @job_public_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job = PublicJobSelector().get_published(job_id)
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        JobPostingRepository().increment_view_count(job)
        job.refresh_from_db(fields=["view_count"])
        return self.success_response(JobPostingSerializer(job).data)
