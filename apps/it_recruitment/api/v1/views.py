from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle, ResumeUploadThrottle

from apps.accounts.profiles.api.v1.serializers import (
    JobSeekerProfileSerializer,
    RecruiterProfileSerializer,
)
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.permissions.profile_permissions import (
    CanManageOwnProfile,
    IsProfileOwner,
)
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.it_recruitment.api.schema import (
    company_create_schema,
    company_detail_schema,
    company_list_schema,
    company_update_schema,
    job_close_schema,
    job_create_schema,
    job_detail_schema,
    job_inbox_schema,
    job_list_schema,
    job_publish_schema,
    job_update_schema,
    recruiter_job_list_schema,
)
from apps.it_recruitment.api.v1.serializers import (
    CompanySerializer,
    CompanyUpdateSerializer,
    JobPostingCreateSerializer,
    JobPostingSerializer,
    JobPostingUpdateSerializer,
)
from apps.companies.models import Company
from apps.companies.selectors.company_selector import (
    CompanyMemberSelector,
    CompanySelector,
)
from apps.companies.services.company_service import CompanyService, JobPostingService
from apps.core.pagination import paginate_envelope
from apps.core.permissions.roles import IsJobSeeker, IsRecruiter
from apps.core.views.base import EnvelopeAPIView
from apps.it_recruitment.selectors.profile_selector import (
    JobSeekerProfileSelector,
    RecruiterProfileSelector,
)
from apps.jobs.models import JobPosting
from apps.jobs.selectors.job_selector import JobPostingSelector


class JobSeekerProfileView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsJobSeeker]
    throttle_classes = [ResumeUploadThrottle]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsJobSeeker(), CanManageOwnProfile()]
        if self.request.method == "PATCH":
            return [permissions.IsAuthenticated(), IsJobSeeker(), IsProfileOwner()]
        return super().get_permissions()

    from drf_spectacular.utils import extend_schema

    @extend_schema(responses={200: JobSeekerProfileSerializer})
    @extend_schema(responses={200: dict})
    def get(self, request):
        profile = JobSeekerProfileSelector().for_user(request.user)
        if not profile:
            return self.success_response(None)
        return self.success_response(JobSeekerProfileSerializer(profile).data)

    @extend_schema(request=JobSeekerProfileSerializer, responses={201: JobSeekerProfileSerializer})
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        profile = ProfileService().create_profile(
            user=request.user, profile_type=ProfileType.JOB_SEEKER, data=request.data
        )
        return self.success_response(
            JobSeekerProfileSerializer(profile).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=JobSeekerProfileSerializer, responses={200: JobSeekerProfileSerializer})
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request):
        profile = ProfileService().update_profile(
            user=request.user, profile_type=ProfileType.JOB_SEEKER, data=request.data
        )
        return self.success_response(JobSeekerProfileSerializer(profile).data)


class RecruiterProfileView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ResumeUploadThrottle]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsRecruiter(), CanManageOwnProfile()]
        if self.request.method == "PATCH":
            return [permissions.IsAuthenticated(), IsRecruiter(), IsProfileOwner()]
        return super().get_permissions()

    from drf_spectacular.utils import extend_schema

    @extend_schema(responses={200: RecruiterProfileSerializer})
    @extend_schema(responses={200: dict})
    def get(self, request):
        profile = RecruiterProfileSelector().for_user(request.user)
        if not profile:
            return self.success_response(None)
        return self.success_response(RecruiterProfileSerializer(profile).data)

    @extend_schema(request=RecruiterProfileSerializer, responses={201: RecruiterProfileSerializer})
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        profile = ProfileService().create_profile(
            user=request.user, profile_type=ProfileType.RECRUITER, data=request.data
        )
        return self.success_response(
            RecruiterProfileSerializer(profile).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=RecruiterProfileSerializer, responses={200: RecruiterProfileSerializer})
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request):
        profile = ProfileService().update_profile(
            user=request.user, profile_type=ProfileType.RECRUITER, data=request.data
        )
        return self.success_response(RecruiterProfileSerializer(profile).data)


class CompanyListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @company_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        companies = Company.objects.none()
        if recruiter:
            companies = CompanySelector().for_recruiter(recruiter)
        return paginate_envelope(request, companies, CompanySerializer)

    @company_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        company = CompanyService().create_company(
            recruiter=recruiter, data=request.data
        )
        return self.success_response(
            CompanySerializer(company).data, status=status.HTTP_201_CREATED
        )


class CompanyDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @company_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        if not CompanyMemberSelector().is_member(recruiter, company_id):
            return self.error_response(
                "PERMISSION_DENIED", "You are not a member of this company.", status=403
            )
        company = CompanySelector().get_or_none(company_id)
        if not company:
            return self.error_response("NOT_FOUND", "Company not found.", status=404)
        return self.success_response(CompanySerializer(company).data)

    @company_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, company_id):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        company = CompanySelector().get_or_none(company_id)
        if not company:
            return self.error_response("NOT_FOUND", "Company not found.", status=404)
        serializer = CompanyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        company = CompanyService().update_company(
            company=company, recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(CompanySerializer(company).data)


class JobListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @job_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        jobs = JobPostingSelector().published(search=request.query_params.get("search"))
        return paginate_envelope(request, jobs, JobPostingSerializer)

    @job_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = JobPostingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        company = CompanySelector().get_or_none(serializer.validated_data["company_id"])
        if not company:
            return self.error_response("NOT_FOUND", "Company not found.", status=404)
        if not CompanyMemberSelector().is_member(recruiter, company.pk):
            return self.error_response(
                "PERMISSION_DENIED", "You are not a member of this company.", status=403
            )
        job = JobPostingService().create_draft(
            company=company, recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(
            JobPostingSerializer(job).data, status=status.HTTP_201_CREATED
        )


class RecruiterJobListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @recruiter_job_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        jobs = JobPosting.objects.none()
        if recruiter:
            jobs = JobPostingSelector().for_recruiter(recruiter)
        return paginate_envelope(request, jobs, JobPostingSerializer)


class JobDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @job_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job = JobPostingSelector().filter_by(pk=job_id).first()
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        if job.status != JobPosting.JobStatus.PUBLISHED:
            recruiter = RecruiterProfileSelector().for_user(request.user)
            if not recruiter or not CompanyMemberSelector().is_member(
                recruiter, job.company_id
            ):
                return self.error_response("NOT_FOUND", "Job not found.", status=404)
        return self.success_response(JobPostingSerializer(job).data)

    @job_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, job_id):
        job = JobPostingSelector().filter_by(pk=job_id).first()
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        serializer = JobPostingUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        job = JobPostingService().update_draft(
            job, recruiter=recruiter, data=serializer.validated_data
        )
        return self.success_response(JobPostingSerializer(job).data)


class JobPublishView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @job_publish_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        job = JobPostingSelector().filter_by(pk=job_id).first()
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        job = JobPostingService().publish(job, recruiter=recruiter)
        return self.success_response(JobPostingSerializer(job).data)


class JobCloseView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @job_close_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id):
        job = JobPostingSelector().filter_by(pk=job_id).first()
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PROFILE_REQUIRED", "Recruiter profile required.", status=400
            )
        job = JobPostingService().close(job, recruiter=recruiter)
        return self.success_response(JobPostingSerializer(job).data)
