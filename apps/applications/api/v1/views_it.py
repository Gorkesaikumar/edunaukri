from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status

from django.core.exceptions import PermissionDenied
from django.http import FileResponse

from apps.applications.constants.enums import JobApplicationStatus
from apps.authentication.permissions.throttles import ApplicationThrottle, ResumeUploadThrottle
from apps.applications.api.schema import (
    application_create_schema,
    application_detail_schema,
    application_history_schema,
    application_notes_schema,
    application_search_schema,
    application_statistics_schema,
    application_status_schema,
    application_timeline_schema,
    application_certificates_schema,
    application_withdraw_schema,
    company_application_list_schema,
    recruiter_application_list_schema,
    seeker_application_list_schema,
)
from apps.applications.api.v1.serializers import (
    JobApplicationCreateSerializer,
    JobApplicationInterviewScheduleSerializer,
    JobApplicationInterviewSerializer,
    JobApplicationInterviewUpdateSerializer,
    JobApplicationNotesSerializer,
    JobApplicationSerializer,
    JobApplicationStatusHistorySerializer,
    JobApplicationStatusSerializer,
    JobApplicationTimelineSerializer,
)
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.services.resume_recruiter_access_service import (
    ResumeRecruiterAccessService,
)
from apps.it_recruitment.services.certificate_recruiter_access_service import (
    CertificateRecruiterAccessService,
)
from apps.applications.models import JobApplication
from apps.applications.permissions.application_permissions import (
    CanManageJobApplicationStatus,
    CanViewJobApplication,
)
from apps.applications.selectors.application_selector import (
    ApplicationSearchSelector,
    JobApplicationSelector,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.application_document_service import (
    ApplicationDocumentService,
)
from apps.applications.services.application_service import JobApplicationService
from apps.applications.services.application_statistics_service import (
    ApplicationStatisticsService,
)
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsITDomainUser
from apps.core.permissions.roles import IsRecruiter
from apps.core.views.base import EnvelopeAPIView
from apps.it_recruitment.api.schema import job_inbox_schema
from apps.it_recruitment.selectors.profile_selector import (
    JobSeekerProfileSelector,
    RecruiterProfileSelector,
)
from apps.jobs.selectors.job_selector import JobPostingSelector, PublicJobSelector


class JobApplicationListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ApplicationThrottle]

    @seeker_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        seeker = JobSeekerProfileSelector().for_user(request.user)
        queryset = JobApplication.objects.none()
        if seeker:
            queryset = JobApplicationSelector().for_seeker(
                seeker, status=request.query_params.get("status")
            )
        return paginate_envelope(request, queryset, JobApplicationSerializer)

    @application_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = JobApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seeker = JobSeekerProfileSelector().for_user(request.user)
        if not seeker:
            return self.error_response(
                "PROFILE_REQUIRED", "Job seeker profile required.", status=400
            )
        job = PublicJobSelector().get_published(
            serializer.validated_data["job_posting_id"]
        )
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        resume_file = ApplicationDocumentService().resolve_resume_for_seeker(
            seeker=seeker,
            user=request.user,
            resume_file_id=serializer.validated_data.get("resume_file_id"),
        )
        data = serializer.validated_data
        application = JobApplicationService().apply(
            job_posting=job,
            job_seeker=seeker,
            cover_letter=data.get("cover_letter", ""),
            resume_file=resume_file,
            expected_salary=data.get("expected_salary"),
            notice_period=data.get("notice_period", ""),
            current_location=data.get("current_location", ""),
            source=data.get("source", ""),
        )
        return self.success_response(
            JobApplicationSerializer(application).data, status=status.HTTP_201_CREATED
        )


class RecruiterJobApplicationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @recruiter_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        queryset = JobApplication.objects.none()
        if recruiter:
            queryset = ApplicationSearchSelector().search(
                query=request.query_params.get("q", ""),
                status=request.query_params.get("status", ""),
                job_posting_id=request.query_params.get("job_posting_id"),
                company_id=request.query_params.get("company_id"),
                recruiter=recruiter,
                sort=request.query_params.get("sort", "recent"),
            )
        return paginate_envelope(request, queryset, JobApplicationSerializer)


class CompanyJobApplicationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @company_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, company_id):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PERMISSION_DENIED", "Recruiter profile required.", status=403
            )
        from apps.companies.selectors.company_selector import CompanyMemberSelector

        if not CompanyMemberSelector().is_member(recruiter, company_id):
            return self.error_response(
                "PERMISSION_DENIED", "You are not a member of this company.", status=403
            )
        queryset = JobApplicationSelector().for_company(
            company_id,
            status=request.query_params.get("status"),
            job_posting_id=request.query_params.get("job_posting_id"),
        )
        return paginate_envelope(request, queryset, JobApplicationSerializer)


class ApplicationStatisticsView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @application_statistics_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return self.error_response(
                "PERMISSION_DENIED", "Recruiter profile required.", status=403
            )
        company_id = request.query_params.get("company_id")
        if company_id:
            stats = ApplicationStatisticsService().company_dashboard(
                company_id=company_id, recruiter=recruiter
            )
        else:
            stats = ApplicationStatisticsService().recruiter_dashboard(recruiter)
        return self.success_response(stats)


class JobPostingApplicationInboxView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    throttle_classes = [ApplicationThrottle]

    @job_inbox_schema
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job = JobPostingSelector().filter_by(pk=job_id).first()
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        ApplicationAuthorizationService().ensure_can_view_it_applications_for_job(
            job, request.user
        )
        queryset = JobApplicationSelector().for_job_posting(
            job, status=request.query_params.get("status")
        )
        return paginate_envelope(request, queryset, JobApplicationSerializer)


class JobApplicationStatusView(EnvelopeAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsITDomainUser,
        CanManageJobApplicationStatus,
    ]
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
        data = serializer.validated_data.copy()
        interview_payload = data.pop("interview", None)
        new_status = data["status"]
        application = JobApplicationService().update_status_for_actor(
            application,
            new_status,
            data.get("notes", ""),
            actor=request.user,
            rejection_reason=data.get("rejection_reason", ""),
        )
        if interview_payload and new_status == JobApplicationStatus.INTERVIEW_SCHEDULED:
            try:
                InterviewSchedulingService().schedule(
                    application,
                    actor=request.user,
                    transition_status=False,
                    notes=interview_payload.get("notes", data.get("notes", "")),
                    **{
                        k: v
                        for k, v in interview_payload.items()
                        if k not in {"notes", "transition_status"}
                    },
                )
            except PermissionDenied as exc:
                return self.error_response("FORBIDDEN", str(exc), status=403)
        return self.success_response(JobApplicationSerializer(application).data)


class JobApplicationWithdrawView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ApplicationThrottle]

    @application_withdraw_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        application = JobApplicationService().withdraw(application, actor=request.user)
        return self.success_response(JobApplicationSerializer(application).data)


class JobApplicationNotesView(EnvelopeAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsITDomainUser,
        CanViewJobApplication,
    ]
    throttle_classes = [ApplicationThrottle]

    @application_notes_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        serializer = JobApplicationNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = JobApplicationService()
        if "recruiter_notes" in data:
            application = service.add_recruiter_notes(
                application, notes=data["recruiter_notes"], actor=request.user
            )
        if "internal_remarks" in data:
            application = service.add_internal_remarks(
                application, remarks=data["internal_remarks"], actor=request.user
            )
        if "candidate_notes" in data:
            application = service.add_candidate_notes(
                application, notes=data["candidate_notes"], actor=request.user
            )
        return self.success_response(JobApplicationSerializer(application).data)


class JobApplicationStatusHistoryView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ApplicationThrottle]

    @application_history_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_it_application(
            application, request.user
        )
        from apps.applications.selectors.status_history_selector import (
            JobApplicationStatusHistorySelector,
        )

        history = JobApplicationStatusHistorySelector().for_application(application)
        return self.success_response(
            JobApplicationStatusHistorySerializer(history, many=True).data
        )


class JobApplicationTimelineView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ApplicationThrottle]

    @application_timeline_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_it_application(
            application, request.user
        )
        from apps.applications.selectors.timeline_selector import (
            JobApplicationTimelineSelector,
        )

        timeline = JobApplicationTimelineSelector().for_application(application)
        return self.success_response(
            JobApplicationTimelineSerializer(timeline, many=True).data
        )


class JobApplicationDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ApplicationThrottle]

    @application_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_it_application(
            application, request.user
        )
        payload = JobApplicationSerializer(application).data
        from apps.it_recruitment.services.jobseeker_privacy_service import (
            JobSeekerPrivacyService,
        )

        privacy = JobSeekerPrivacyService()
        payload.update(
            privacy.recruiter_permissions_for_application(application, request.user)
        )
        payload["certificates"] = (
            CertificateRecruiterAccessService().list_for_application(
                application, actor=request.user
            )
        )
        payload["certificate_count"] = len(payload["certificates"])
        return self.success_response(payload)

    @application_detail_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        JobApplicationService().soft_delete(application, actor=request.user)
        return self.success_response({"deleted": True})


class JobApplicationResumeDownloadView(EnvelopeAPIView):
    """Recruiter or applicant download of resume attached to an application."""

    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ResumeUploadThrottle, ApplicationThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = (
            JobApplication.objects.filter(pk=application_id, is_deleted=False)
            .select_related(
                "resume_file", "job_seeker", "job_seeker__resume_file", "job_posting"
            )
            .first()
        )
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        try:
            access = ResumeRecruiterAccessService()
            stored = access.resolve_application_resume(application, actor=request.user)
            from apps.it_recruitment.selectors.profile_selector import (
                JobSeekerProfileSelector,
            )

            seeker = JobSeekerProfileSelector().for_user(request.user)
            if not seeker or seeker.pk != application.job_seeker_id:
                access.record_recruiter_download(application, actor=request.user)
            path = StorageService().get_absolute_path(stored)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=stored.original_filename
            )
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        except FileNotFoundError:
            return self.error_response(
                "NOT_FOUND", "Resume file missing from storage.", status=404
            )


class JobApplicationCertificatesView(EnvelopeAPIView):
    """List candidate certificates for an application (recruiter, admin, or applicant)."""

    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ApplicationThrottle]

    @application_certificates_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = (
            JobApplication.objects.filter(pk=application_id, is_deleted=False)
            .select_related("job_seeker", "job_posting")
            .first()
        )
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        try:
            items = CertificateRecruiterAccessService().list_for_application(
                application, actor=request.user
            )
            return self.success_response({"items": items, "total": len(items)})
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)


class JobApplicationCertificateDownloadView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ResumeUploadThrottle, ApplicationThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, application_id, certification_id):
        application = (
            JobApplication.objects.filter(pk=application_id, is_deleted=False)
            .select_related("job_seeker", "job_posting")
            .first()
        )
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        try:
            access = CertificateRecruiterAccessService()
            cert, stored = access.resolve_certificate_file(
                application, certification_id, actor=request.user
            )
            if CertificateRecruiterAccessService.is_recruiter_actor(
                application, request.user
            ):
                access.record_recruiter_download(application, cert, actor=request.user)
            path = StorageService().get_absolute_path(stored)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=stored.original_filename
            )
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        except FileNotFoundError:
            return self.error_response(
                "NOT_FOUND", "Certificate file missing from storage.", status=404
            )


class JobApplicationCertificatePreviewView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [ResumeUploadThrottle, ApplicationThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, application_id, certification_id):
        application = (
            JobApplication.objects.filter(pk=application_id, is_deleted=False)
            .select_related("job_seeker", "job_posting")
            .first()
        )
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        try:
            access = CertificateRecruiterAccessService()
            cert, stored = access.resolve_certificate_file(
                application, certification_id, actor=request.user
            )
            if CertificateRecruiterAccessService.is_recruiter_actor(
                application, request.user
            ):
                access.record_recruiter_preview(application, cert, actor=request.user)
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
            return self.error_response(
                "UNSUPPORTED",
                "Preview is available for PDF and image certificates only.",
                status=400,
            )
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        except FileNotFoundError:
            return self.error_response(
                "NOT_FOUND", "Certificate file missing from storage.", status=404
            )


class JobApplicationInterviewListCreateView(EnvelopeAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsITDomainUser,
        CanManageJobApplicationStatus,
    ]
    throttle_classes = [ApplicationThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_it_application(
            application, request.user
        )
        interviews = InterviewSelector().for_application(application)
        return self.success_response(
            JobApplicationInterviewSerializer(interviews, many=True).data
        )

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        serializer = JobApplicationInterviewScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            interview = InterviewSchedulingService().schedule(
                application,
                actor=request.user,
                scheduled_at=data["scheduled_at"],
                round_type=data.get("round_type", "technical"),
                round_label=data.get("round_label", ""),
                interview_type=data.get("interview_type", "Technical Interview"),
                mode=data.get("mode", "online"),
                duration_minutes=data.get("duration_minutes", 45),
                timezone_label=data.get("timezone_label", "IST"),
                meet_url=data.get("meet_url", ""),
                location=data.get("location", ""),
                panel=data.get("panel"),
                instructions=data.get("instructions", ""),
                required_documents=data.get("required_documents"),
                notes=data.get("notes", ""),
                transition_status=data.get("transition_status", True),
            )
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        return self.success_response(
            JobApplicationInterviewSerializer(interview).data,
            status=status.HTTP_201_CREATED,
        )


class JobApplicationInterviewDetailView(EnvelopeAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsITDomainUser,
        CanManageJobApplicationStatus,
    ]
    throttle_classes = [ApplicationThrottle]

    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id, interview_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        interview = InterviewSelector().get_active(interview_id)
        if not interview or interview.application_id != application.pk:
            return self.error_response("NOT_FOUND", "Interview not found.", status=404)
        serializer = JobApplicationInterviewUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = InterviewSchedulingService().update_interview(
            interview, actor=request.user, **serializer.validated_data
        )
        return self.success_response(JobApplicationInterviewSerializer(interview).data)

    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, application_id, interview_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        interview = InterviewSelector().get_active(interview_id)
        if not interview or interview.application_id != application.pk:
            return self.error_response("NOT_FOUND", "Interview not found.", status=404)
        reason = request.data.get("reason", "")
        interview = InterviewSchedulingService().cancel(
            interview, actor=request.user, reason=reason
        )
        return self.success_response(JobApplicationInterviewSerializer(interview).data)
