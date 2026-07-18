"""Recruiter portal web APIs — profile, company, and job management."""

from __future__ import annotations

import json

from django.http import FileResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.selectors.application_selector import JobApplicationSelector
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.application_service import JobApplicationService
from apps.companies.models import Company
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.companies.services.company_service import CompanyService, JobPostingService
from apps.companies.services.recruiter_company_service import RecruiterCompanyService
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    DomainException,
    PermissionDeniedException,
    ValidationException,
)
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.resume_recruiter_access_service import (
    ResumeRecruiterAccessService,
)
from apps.it_recruitment.views.recruiter_api_base import RecruiterScopedAPIView
from apps.jobs.selectors.job_selector import JobPostingSelector
from apps.jobs.services.job_lifecycle_service import JobLifecycleService
from apps.jobs.services.job_service import JobService


def _get_profile(user) -> RecruiterProfile | None:
    return (
        RecruiterProfile.objects.filter(user=user, is_deleted=False)
        .select_related("user")
        .first()
    )


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _error_response(exc):
    if isinstance(exc, ConflictException):
        from apps.companies.services.recruiter_company_service import (
            RecruiterCompanyService,
        )

        return JsonResponse(
            {"success": False, "error": RecruiterCompanyService.friendly_error(exc)},
            status=409,
        )
    if isinstance(exc, (ValidationException, BusinessLogicException, DomainException)):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _authorized(request) -> RecruiterProfile | None:
    if not RoleAssignmentService().user_has_it_role(
        request.user, ITUserRoleType.RECRUITER
    ):
        return None
    return _get_profile(request.user)


def _parse_json(request) -> dict:
    return json.loads(request.body.decode("utf-8") or "{}")


def _primary_company(profile: RecruiterProfile) -> Company | None:
    membership = (
        CompanyMemberSelector()
        .for_recruiter(profile)
        .select_related("company")
        .order_by("-is_primary", "-created_at")
        .first()
    )
    return membership.company if membership else None


def _get_application_for_recruiter(profile: RecruiterProfile, application_id):
    application = JobApplicationSelector().get_active(application_id)
    if not application:
        return None
    try:
        ApplicationAuthorizationService().ensure_can_view_it_application(
            application, profile.user
        )
    except PermissionDeniedException:
        return None
    return application


def _get_job_for_recruiter(profile: RecruiterProfile, job_id):
    return JobPostingSelector().for_recruiter(profile).filter(pk=job_id).first()


def _get_interview_for_recruiter(profile: RecruiterProfile, interview_id):
    from apps.applications.services.interview_scheduling_service import (
        InterviewSelector,
    )

    interview = InterviewSelector().get_active(interview_id)
    if not interview:
        return None
    try:
        ApplicationAuthorizationService().ensure_can_view_it_application(
            interview.application, profile.user
        )
    except PermissionDeniedException:
        return None
    return interview


@method_decorator(csrf_protect, name="dispatch")
class RecruiterProfileAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def patch(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            updated = ProfileService().update_profile(
                user=request.user, profile_type=ProfileType.RECRUITER, data=data
            )
            from apps.it_recruitment.services.recruiter_profile_portal_service import (
                RecruiterProfilePortalService,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Profile updated.",
                    "data": RecruiterProfilePortalService()._serialize_recruiter(
                        updated
                    ),
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterCompanyCreateAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        try:
            data = _parse_json(request)
            company = RecruiterCompanyService().create_company(
                recruiter=profile, data=data
            )
            from apps.it_recruitment.services.recruiter_profile_portal_service import (
                RecruiterProfilePortalService,
            )

            ctx = RecruiterProfilePortalService().build(profile)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Company profile created and verified successfully.",
                    "data": {
                        "company_id": str(company.pk),
                        "company": ctx.company,
                        "verified": company.is_verified,
                    },
                },
                status=201,
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid request payload."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            ConflictException,
            DomainException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterCompanyAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"

    def patch(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        company = _primary_company(profile)
        if not company:
            return JsonResponse(
                {"success": False, "error": "No company profile found."}, status=404
            )
        try:
            data = _parse_json(request)
            company = RecruiterCompanyService().update_company(
                company=company, recruiter=profile, data=data
            )
            from apps.it_recruitment.services.recruiter_profile_portal_service import (
                RecruiterProfilePortalService,
            )

            ctx = RecruiterProfilePortalService().build(profile)
            message = "Company profile updated successfully."
            if company.is_verified:
                message = "Company profile updated and verified successfully."
            return JsonResponse(
                {"success": True, "message": message, "data": ctx.company}
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobCreateAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        company = _primary_company(profile)
        if not company:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Create a company profile before posting jobs.",
                },
                status=400,
            )
        try:
            data = _parse_json(request)
            title = (data.get("title") or "").strip()
            description = (data.get("description") or "").strip()
            if not title:
                return JsonResponse(
                    {"success": False, "error": "Job title is required."}, status=400
                )
            if not description:
                return JsonResponse(
                    {"success": False, "error": "Job description is required."},
                    status=400,
                )
            job = JobPostingService().create_draft(
                company=company,
                recruiter=profile,
                data=data,
            )
            from apps.authentication.services.portal_url_service import PortalURLService

            pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
            from apps.it_recruitment.services.recruiter_jobs_portal_service import (
                RecruiterJobsPortalService,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Draft job created.",
                    "data": RecruiterJobsPortalService._serialize_job(job, pu),
                },
                status=201,
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobPublishAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            JobPostingService().publish(job, recruiter=profile)
            return JsonResponse(
                {"success": True, "message": "Job published successfully."}
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobCloseAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            JobPostingService().close(job, recruiter=profile)
            return JsonResponse({"success": True, "message": "Job closed."})
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterApplicationStatusAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["patch"]

    def patch(self, request, application_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        application = _get_application_for_recruiter(profile, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request)
            new_status = (data.get("status") or "").strip()
            if not new_status:
                return JsonResponse(
                    {"success": False, "error": "Status is required."}, status=400
                )
            updated = JobApplicationService().update_status_for_actor(
                application,
                new_status,
                data.get("notes", ""),
                actor=request.user,
                rejection_reason=data.get("rejection_reason", ""),
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Application status updated.",
                    "data": {"id": str(updated.pk), "status": updated.status},
                }
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterApplicationNotesAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["patch"]

    def patch(self, request, application_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        application = _get_application_for_recruiter(profile, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request)
            notes = data.get("recruiter_notes")
            if notes is None:
                return JsonResponse(
                    {"success": False, "error": "recruiter_notes is required."},
                    status=400,
                )
            updated = JobApplicationService().add_recruiter_notes(
                application, notes=notes, actor=request.user
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Notes saved.",
                    "data": {
                        "id": str(updated.pk),
                        "recruiter_notes": updated.recruiter_notes,
                    },
                }
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterApplicationResumeAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request, application_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        application = _get_application_for_recruiter(profile, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            access = ResumeRecruiterAccessService()
            stored = access.resolve_application_resume(application, actor=request.user)
            access.record_recruiter_download(application, actor=request.user)
            path = StorageService().get_absolute_path(stored)
            inline = request.GET.get("preview") == "1"
            response = FileResponse(path.open("rb"), filename=stored.original_filename)
            if inline:
                response["Content-Disposition"] = (
                    f'inline; filename="{stored.original_filename}"'
                )
            else:
                response["Content-Disposition"] = (
                    f'attachment; filename="{stored.original_filename}"'
                )
            return response
        except PermissionDeniedException as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=403)
        except FileNotFoundError:
            return JsonResponse(
                {"success": False, "error": "Resume file missing from storage."},
                status=404,
            )


@method_decorator(csrf_protect, name="dispatch")
class RecruiterMarketplaceResumeAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request, seeker_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.it_recruitment.models import JobSeekerProfile
        from apps.it_recruitment.services.jobseeker_privacy_service import (
            JobSeekerPrivacyService,
        )

        seeker = (
            JobSeekerProfile.objects.filter(pk=seeker_id, is_deleted=False)
            .select_related("resume_file")
            .first()
        )
        if not seeker:
            return JsonResponse(
                {"success": False, "error": "Candidate not found."}, status=404
            )
        try:
            JobSeekerPrivacyService().ensure_can_download_resume(seeker, request.user)
            stored = seeker.resume_file
            if not stored:
                return JsonResponse(
                    {"success": False, "error": "Resume not available."}, status=404
                )
            path = StorageService().get_absolute_path(stored)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=stored.original_filename
            )
        except PermissionDeniedException as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=403)
        except FileNotFoundError:
            return JsonResponse(
                {"success": False, "error": "Resume file missing from storage."},
                status=404,
            )


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobPauseAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = _get_job_for_recruiter(profile, job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            JobLifecycleService().pause(job_posting=job, recruiter=profile)
            return JsonResponse(
                {"success": True, "message": "Hiring paused for this job."}
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobDuplicateAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = _get_job_for_recruiter(profile, job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            clone = JobService().duplicate_job(job_posting=job, recruiter=profile)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Job duplicated as draft.",
                    "data": {"id": str(clone.pk), "title": clone.title},
                }
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobDeleteAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = _get_job_for_recruiter(profile, job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            JobService().soft_delete(job_posting=job, recruiter=profile)
            return JsonResponse({"success": True, "message": "Job deleted."})
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterApplicationDetailAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request, application_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.it_recruitment.services.recruiter_candidates_portal_service import (
            RecruiterCandidatesPortalService,
        )

        data = RecruiterCandidatesPortalService().get_detail(profile, application_id)
        if not data:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        return JsonResponse({"success": True, "data": data})


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewCancelAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, interview_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        interview = _get_interview_for_recruiter(profile, interview_id)
        if not interview:
            return JsonResponse(
                {"success": False, "error": "Interview not found."}, status=404
            )
        try:
            from apps.applications.services.interview_scheduling_service import (
                InterviewSchedulingService,
            )

            data = _parse_json(request) if request.body else {}
            InterviewSchedulingService().cancel(
                interview,
                actor=request.user,
                reason=(data.get("reason") or "").strip(),
            )
            return JsonResponse({"success": True, "message": "Interview cancelled."})
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewRescheduleAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["patch"]

    def patch(self, request, interview_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        interview = _get_interview_for_recruiter(profile, interview_id)
        if not interview:
            return JsonResponse(
                {"success": False, "error": "Interview not found."}, status=404
            )
        try:
            from django.utils import timezone
            from django.utils.dateparse import parse_datetime

            from apps.applications.services.interview_scheduling_service import (
                InterviewSchedulingService,
            )

            data = _parse_json(request)
            scheduled_raw = (data.get("scheduled_at") or "").strip()
            if not scheduled_raw:
                return JsonResponse(
                    {"success": False, "error": "scheduled_at is required."}, status=400
                )
            scheduled_at = parse_datetime(scheduled_raw)
            if scheduled_at is None:
                return JsonResponse(
                    {"success": False, "error": "Invalid scheduled_at."}, status=400
                )
            if timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at)
            InterviewSchedulingService().update_interview(
                interview,
                actor=request.user,
                scheduled_at=scheduled_at,
            )
            return JsonResponse({"success": True, "message": "Interview rescheduled."})
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobReopenAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = _get_job_for_recruiter(profile, job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            JobLifecycleService().reopen(job_posting=job, recruiter=profile)
            return JsonResponse(
                {"success": True, "message": "Job reopened and published."}
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobArchiveAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        job = _get_job_for_recruiter(profile, job_id)
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            JobLifecycleService().archive(job_posting=job, recruiter=profile)
            return JsonResponse({"success": True, "message": "Job archived."})
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobsListAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.it_recruitment.services.recruiter_jobs_portal_service import (
            RecruiterJobsPortalService,
        )

        status = (request.GET.get("status") or "").strip()
        q = (request.GET.get("q") or "").strip()
        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        ctx = RecruiterJobsPortalService().build(
            profile, status_filter=status, q=q, page=page
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "jobs": ctx.jobs,
                    "stats": ctx.stats,
                    "pagination": ctx.pagination,
                    "filters": ctx.filters,
                },
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobApplicantsAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.it_recruitment.services.recruiter_candidates_portal_service import (
            RecruiterCandidatesPortalService,
        )

        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        result = RecruiterCandidatesPortalService().list_for_job(
            profile, job_id, q=q, status=status, page=page
        )
        if result.get("error") and not result.get("applications"):
            return JsonResponse(
                {"success": False, "error": result["error"]}, status=404
            )
        return JsonResponse(result)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewScheduleAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        application = _get_application_for_recruiter(profile, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            from django.utils import timezone
            from django.utils.dateparse import parse_datetime

            from apps.applications.services.interview_scheduling_service import (
                InterviewSchedulingService,
            )

            data = _parse_json(request)
            scheduled_raw = (data.get("scheduled_at") or "").strip()
            if not scheduled_raw:
                return JsonResponse(
                    {"success": False, "error": "scheduled_at is required."}, status=400
                )
            scheduled_at = parse_datetime(scheduled_raw)
            if scheduled_at is None:
                return JsonResponse(
                    {"success": False, "error": "Invalid scheduled_at."}, status=400
                )
            if timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at)
            mode = (data.get("mode") or "online").strip().lower()
            interview = InterviewSchedulingService().schedule(
                application,
                actor=request.user,
                scheduled_at=scheduled_at,
                mode=mode,
                meet_url=(data.get("meet_url") or "").strip(),
                location=(data.get("location") or "").strip(),
                instructions=(
                    data.get("notes") or data.get("instructions") or ""
                ).strip(),
                round_label=(
                    data.get("interview_type") or data.get("round_label") or "Interview"
                ).strip(),
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Interview scheduled.",
                    "data": {
                        "id": str(interview.pk),
                        "scheduled_at": scheduled_at.isoformat(),
                    },
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterJobDetailAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get", "patch", "put"]

    def get(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.jobs.selectors.job_selector import JobPostingSelector

        job = JobPostingSelector().for_recruiter(profile).filter(pk=job_id).first()
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        from apps.authentication.services.portal_url_service import PortalURLService
        from apps.it_recruitment.services.recruiter_jobs_portal_service import (
            RecruiterJobsPortalService,
        )

        pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
        return JsonResponse(
            {
                "success": True,
                "data": RecruiterJobsPortalService._serialize_job(job, pu),
            }
        )

    def patch(self, request, job_id):
        return self._update(request, job_id)

    def put(self, request, job_id):
        return self._update(request, job_id)

    def _update(self, request, job_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.jobs.selectors.job_selector import JobPostingSelector

        job = JobPostingSelector().for_recruiter(profile).filter(pk=job_id).first()
        if not job:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )
        try:
            data = _parse_json(request)
            updated_job = JobPostingService().update_draft(
                job_posting=job,
                recruiter=profile,
                data=data,
            )
            from apps.authentication.services.portal_url_service import PortalURLService
            from apps.it_recruitment.services.recruiter_jobs_portal_service import (
                RecruiterJobsPortalService,
            )

            pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Job updated successfully.",
                    "data": RecruiterJobsPortalService._serialize_job(updated_job, pu),
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


class RecruiterSkillSuggestAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.jobs.models import Skill

        q = (request.GET.get("q") or "").strip()
        if q:
            skills = Skill.objects.filter(is_active=True, name__icontains=q).order_by(
                "name"
            )[:15]
        else:
            skills = Skill.objects.filter(is_active=True).order_by("name")[:15]
        return JsonResponse(
            {
                "success": True,
                "data": [
                    {"id": str(s.pk), "name": s.name, "category": s.category}
                    for s in skills
                ],
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class RecruiterApplicantsListAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.it_recruitment.services.recruiter_candidates_portal_service import (
            RecruiterCandidatesPortalService,
        )

        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        payload = RecruiterCandidatesPortalService().build_list_payload(
            profile,
            q=(request.GET.get("q") or "").strip(),
            status=(request.GET.get("status") or "").strip(),
            job_id=(request.GET.get("job_id") or "").strip(),
            location=(request.GET.get("location") or "").strip(),
            experience_min=(request.GET.get("experience_min") or "").strip(),
            skills=(request.GET.get("skills") or "").strip(),
            education=(request.GET.get("education") or "").strip(),
            date_from=(request.GET.get("date_from") or "").strip(),
            date_to=(request.GET.get("date_to") or "").strip(),
            sort=(request.GET.get("sort") or "recent").strip(),
            page=page,
        )
        return JsonResponse(payload)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewsListAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.it_recruitment.services.recruiter_interview_portal_service import (
            RecruiterInterviewPortalService,
        )

        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        payload = RecruiterInterviewPortalService().build_list_payload(
            profile,
            when=(request.GET.get("when") or "").strip(),
            q=(request.GET.get("q") or "").strip(),
            status=(request.GET.get("status") or "").strip(),
            job_id=(request.GET.get("job_id") or "").strip(),
            mode=(request.GET.get("mode") or "").strip(),
            date_from=(request.GET.get("date_from") or "").strip(),
            date_to=(request.GET.get("date_to") or "").strip(),
            page=page,
        )
        return JsonResponse(payload)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewScheduleCandidatesAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["get"]

    def get(self, request):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        from apps.authentication.services.portal_url_service import PortalURLService
        from apps.it_recruitment.services.recruiter_interview_portal_service import (
            RecruiterInterviewPortalService,
        )

        pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
        candidates = RecruiterInterviewPortalService()._schedule_candidates(profile, pu)
        return JsonResponse({"success": True, "candidates": candidates})


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewFeedbackAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["patch"]

    def patch(self, request, interview_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        interview = _get_interview_for_recruiter(profile, interview_id)
        if not interview:
            return JsonResponse(
                {"success": False, "error": "Interview not found."}, status=404
            )
        try:
            from apps.applications.constants.interview_enums import InterviewStatus
            from apps.applications.services.interview_scheduling_service import (
                InterviewSchedulingService,
            )

            data = _parse_json(request)
            feedback = {
                "technical_skills": data.get("technical_skills"),
                "communication": data.get("communication"),
                "problem_solving": data.get("problem_solving"),
                "behaviour": data.get("behaviour"),
                "overall_rating": data.get("overall_rating"),
                "notes": (data.get("notes") or "").strip(),
                "decision": (data.get("decision") or "").strip(),
            }
            feedback = {k: v for k, v in feedback.items() if v not in (None, "")}
            update_fields = {
                "feedback": feedback,
                "feedback_shared": bool(data.get("feedback_shared")),
            }
            if data.get("decision") == "no_show":
                update_fields["status"] = InterviewStatus.COMPLETED
            InterviewSchedulingService().update_interview(
                interview, actor=request.user, **update_fields
            )

            decision = data.get("decision")
            app = interview.application
            if decision == "proceed":
                from apps.applications.constants.enums import JobApplicationStatus
                from apps.applications.services.application_service import (
                    JobApplicationService,
                )

                if app.status == JobApplicationStatus.INTERVIEW_SCHEDULED:
                    JobApplicationService().update_status_for_actor(
                        app,
                        JobApplicationStatus.INTERVIEW_COMPLETED,
                        "Interview completed — proceed.",
                        actor=request.user,
                    )
            elif decision == "reject":
                from apps.applications.services.application_service import (
                    JobApplicationService,
                )

                JobApplicationService().update_status_for_actor(
                    app,
                    "rejected",
                    (data.get("notes") or "Rejected after interview."),
                    actor=request.user,
                )

            return JsonResponse({"success": True, "message": "Feedback saved."})
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewStatusAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["patch"]

    def patch(self, request, interview_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        interview = _get_interview_for_recruiter(profile, interview_id)
        if not interview:
            return JsonResponse(
                {"success": False, "error": "Interview not found."}, status=404
            )
        try:
            from apps.applications.constants.interview_enums import InterviewStatus
            from apps.applications.services.interview_scheduling_service import (
                InterviewSchedulingService,
            )

            data = _parse_json(request)
            new_status = (data.get("status") or "").strip()
            if new_status not in InterviewStatus.values:
                return JsonResponse(
                    {"success": False, "error": "Invalid status."}, status=400
                )
            InterviewSchedulingService().update_interview(
                interview, actor=request.user, status=new_status
            )
            if new_status == InterviewStatus.COMPLETED:
                from apps.applications.constants.enums import JobApplicationStatus
                from apps.applications.services.application_service import (
                    JobApplicationService,
                )

                app = interview.application
                if app.status == JobApplicationStatus.INTERVIEW_SCHEDULED:
                    JobApplicationService().update_status_for_actor(
                        app,
                        JobApplicationStatus.INTERVIEW_COMPLETED,
                        "Interview marked completed.",
                        actor=request.user,
                    )
            return JsonResponse(
                {"success": True, "message": "Interview status updated."}
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class RecruiterInterviewCompleteAPIView(RecruiterScopedAPIView):
    login_url = "/it/login/recruiter/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        profile = _authorized(request)
        if not profile:
            return _forbidden()
        application = _get_application_for_recruiter(profile, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            import json
            data = json.loads(request.body) if request.body else {}
            from apps.applications.services.recruitment_workflow_service import RecruitmentWorkflowService
            RecruitmentWorkflowService().complete_interview_with_evaluation(
                domain="it",
                application_id=application_id,
                actor=request.user,
                data=data
            )
            return JsonResponse(
                {"success": True, "message": "Interview marked completed with evaluation saved."}
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)

