"""Job Seeker portal views — dashboard and role-protected pages."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.services.application_service import JobApplicationService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_application_portal_service import (
    JobSeekerApplicationPortalService,
)
from apps.it_recruitment.services.jobseeker_dashboard_service import (
    JobSeekerDashboardService,
)
from apps.it_recruitment.services.jobseeker_profile_manage_service import (
    JobSeekerProfileManageService,
)
from apps.it_recruitment.services.jobseeker_interview_portal_service import (
    JobSeekerInterviewPortalService,
)
from apps.it_recruitment.services.jobseeker_certificate_portal_service import (
    JobSeekerCertificatePortalService,
)
from apps.it_recruitment.services.jobseeker_messages_portal_service import (
    JobSeekerMessagesPortalService,
)
from apps.it_recruitment.services.jobseeker_settings_portal_service import (
    JobSeekerSettingsPortalService,
)
from apps.it_recruitment.services.jobseeker_resume_portal_service import (
    JobSeekerResumePortalService,
)
from apps.it_recruitment.services.jobseeker_tracker_service import (
    JobSeekerTrackerService,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    build_sidebar_nav,
    initials_from_name,
    media_url,
)
from apps.authentication.services.identity_service import IdentityService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.jobs.models import JobPosting
from apps.jobs.services.saved_job_service import SavedJobService
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.core.portal_header_config import IT_JOB_SEEKER_HEADER
from apps.notifications.models import Notification


class JobSeekerPortalMixin(LoginRequiredMixin):
    """Shared context for all job seeker portal pages."""

    login_url = "/it/login/job-seeker/"
    required_role = ITUserRoleType.JOB_SEEKER
    sidebar_active_key = "dashboard"
    page_title = ""
    page_description = ""

    def portal_url(self, view_name: str, **kwargs) -> str:
        return PortalURLService.jobseeker(self.request.user, view_name, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and not RoleAssignmentService().user_has_it_role(
                request.user, self.required_role
            )
        ):
            from apps.authentication.services.web_jwt_service import WebJWTService

            other = WebJWTService.resolve_it_dashboard_url(request.user)
            return redirect(other)
        if request.user.is_authenticated and kwargs.get("user_uuid"):
            from apps.authentication.services.identity_service import IdentityService
            if not IdentityService.uuids_match(request.user.pk, kwargs.get("user_uuid")):
                from apps.authentication.services.web_jwt_service import WebJWTService
                other = WebJWTService.resolve_it_dashboard_url(request.user)
                return redirect(other)
        return super().dispatch(request, *args, **kwargs)

    def get_profile(self) -> JobSeekerProfile | None:
        return (
            JobSeekerProfile.objects.filter(user=self.request.user, is_deleted=False)
            .select_related("profile_photo")
            .first()
        )

    def get_portal_header_context(self, profile: JobSeekerProfile | None) -> dict:
        display_name = (
            profile.full_name if profile else self.request.user.email.split("@")[0]
        )
        avatar_url = (
            media_url(profile.profile_photo)
            if profile and profile.profile_photo
            else None
        )
        unread = Notification.objects.filter(
            recipient_domain="it", recipient_id=self.request.user.pk, is_read=False
        ).count()
        notifications, _ = JobSeekerDashboardService()._notifications(self.request.user)
        
        from apps.notifications.services.application_status_notification_service import ApplicationStatusNotificationService
        unread_tracker = ApplicationStatusNotificationService.get_unread_tracker_count(
            self.request.user.pk, "it"
        )
        return {
            "header_user": {
                "display_name": display_name,
                "role_label": "Job Seeker",
                "initials": initials_from_name(
                    display_name, self.request.user.email[:2]
                ),
                "avatar_url": avatar_url,
                "profile_url": PortalURLService.jobseeker(
                    self.request.user, "jobseeker_profile"
                ),
                "user_uuid": IdentityService.public_uuid(self.request.user),
            },
            "header_notifications": notifications,
            "unread_notification_count": unread,
            "unread_tracker_count": unread_tracker,
            "messages_url": PortalURLService.jobseeker(
                self.request.user, "jobseeker_messages"
            ),
            "notifications_url": PortalURLService.jobseeker(
                self.request.user, "jobseeker_notifications"
            ),
            "logout_url": reverse("logout"),
            "search_url": reverse("marketplace_browse_jobs"),
            "portal_header": IT_JOB_SEEKER_HEADER,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        context.update(self.get_portal_header_context(profile))
        context["sidebar"] = build_sidebar_nav(
            self.sidebar_active_key, self.request.user
        )
        context["portal_user_uuid"] = IdentityService.public_uuid(self.request.user)
        context["page_title"] = self.page_title
        context["page_description"] = self.page_description
        context["saved_jobs_count"] = SavedJobService().count(profile) if profile else 0
        return context


class _JobSeekerPageView(JobSeekerPortalMixin, TemplateView):
    """Inner portal page using the dashboard shell."""

    template_name = "it/jobseeker/portal_page.html"


class JobSeekerDashboardView(JobSeekerPortalMixin, TemplateView):
    """Job seeker dashboard at /jobseeker/dashboard/."""

    template_name = "it/jobseeker/dashboard/index.html"
    sidebar_active_key = "dashboard"

    def get_context_data(self, **kwargs):
        context = JobSeekerPortalMixin.get_context_data(self, **kwargs)
        profile = self.get_profile()
        dashboard = JobSeekerDashboardService().build(
            user=self.request.user, profile=profile
        )
        context["dashboard"] = dashboard
        context["dashboard_json"] = {
            "notifications_mark_all_url": self.portal_url(
                "jobseeker_notifications_mark_all_read"
            ),
        }
        return context


class JobSeekerProfileView(JobSeekerPortalMixin, TemplateView):
    sidebar_active_key = "profile"
    template_name = "it/jobseeker/profile/index.html"
    page_title = "My Profile"
    page_description = "Manage your job seeker profile, headline, and skills."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = JobSeekerProfileManageService()
        profile = service.get_profile_queryset().filter(user=self.request.user).first()
        if profile:
            page = service.build_page_context(profile)
            context["profile_page"] = page.to_template_dict()
            context["profile_json"] = service.serialize_profile(profile)
        else:
            context["profile_page"] = None
            context["profile_json"] = {}
        return context


class JobSeekerBrowseJobsView(_JobSeekerPageView):
    """Redirect legacy portal browse route to the public marketplace."""

    def get(self, request, *args, **kwargs):
        return redirect("marketplace_browse_jobs")


class JobSeekerSettingsView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/settings/index.html"
    sidebar_active_key = "settings"
    page_title = "Settings"
    page_description = "Account and security preferences."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            portal = JobSeekerSettingsPortalService()
            page = portal.build(profile, request=self.request)
            context["settings_page"] = page
            context["notification_toggles"] = portal.notification_toggles(
                page.notifications
            )
            context["privacy_toggles"] = portal.privacy_toggles(page.privacy)
        return context


class JobSeekerApplicationsView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/applications/index.html"
    sidebar_active_key = "applications"
    page_title = "Applied Jobs"
    page_description = "Track every application in your pipeline."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            service = JobSeekerApplicationPortalService()
            page = max(1, int(self.request.GET.get("page") or 1))
            context["applications_page"] = service.list_applications(
                profile,
                page=page,
                status=(self.request.GET.get("status") or "").strip(),
                q=(self.request.GET.get("q") or "").strip(),
                active_only=self.request.GET.get("active") == "1",
                interview_only=self.request.GET.get("interview") == "1",
                offer_only=self.request.GET.get("offer") == "1",
                rejected_only=self.request.GET.get("rejected") == "1",
            )
        return context


class JobSeekerSavedJobsView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/saved_jobs.html"
    sidebar_active_key = "saved_jobs"
    page_title = "Saved Jobs"
    page_description = "Jobs you have bookmarked for later."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            page = max(1, int(self.request.GET.get("page") or 1))
            context["saved_jobs_page"] = SavedJobService().list_saved(
                profile, page=page
            )
        return context


class JobSeekerTrackerView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/tracker/index.html"
    sidebar_active_key = "tracker"
    page_title = "Career Tracker"
    page_description = (
        "Your recruitment command center — applications, activity, and insights."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()

        # Mark all tracker notifications as read
        from apps.notifications.models.notification import Notification
        from django.utils import timezone
        Notification.objects.filter(
            recipient_id=self.request.user.pk,
            recipient_domain="it",
            event_type="application.status_changed",
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        context["unread_tracker_count"] = 0

        if profile:
            context["tracker"] = JobSeekerTrackerService().build(
                profile,
                q=(self.request.GET.get("q") or "").strip(),
                status=(self.request.GET.get("status") or "").strip(),
                company=(self.request.GET.get("company") or "").strip(),
                activity_page=max(1, int(self.request.GET.get("page") or 1)),
            )
        return context


class JobSeekerInterviewsView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/interviews/index.html"
    sidebar_active_key = "interviews"
    page_title = "Interviews"
    page_description = "Manage interview invitations, schedules, and outcomes."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["interviews_page"] = (
                JobSeekerInterviewPortalService().list_interviews(
                    profile,
                    page=max(1, int(self.request.GET.get("page") or 1)),
                    q=(self.request.GET.get("q") or "").strip(),
                    status_filter=(self.request.GET.get("status") or "").strip(),
                    when=(self.request.GET.get("when") or "").strip(),
                    company=(self.request.GET.get("company") or "").strip(),
                    mode=(self.request.GET.get("mode") or "").strip(),
                )
            )
        return context


class JobSeekerInterviewDetailView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/interviews/detail.html"
    sidebar_active_key = "interviews"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile is None:
            return context
        detail = JobSeekerInterviewPortalService().get_detail(
            profile, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Interview not found.")
        context["interview"] = detail
        context["page_title"] = detail.job_title
        context["page_description"] = detail.company_name
        return context


class JobSeekerInterviewPrintView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/interviews/print.html"
    sidebar_active_key = "interviews"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile is None:
            return context
        detail = JobSeekerInterviewPortalService().get_detail(
            profile, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Interview not found.")
        context["interview"] = detail
        return context


class JobSeekerResumeView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/resume/index.html"
    sidebar_active_key = "resume"
    page_title = "Resume"
    page_description = "Upload, preview, and manage your resume."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["resume_page"] = JobSeekerResumePortalService().build(profile)
        return context


class JobSeekerCertificatesView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/certificates/index.html"
    sidebar_active_key = "certificates"
    page_title = "Certificates"
    page_description = "Manage your credentials and certifications."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            svc = JobSeekerCertificatePortalService()
            context["cert_page"] = svc.build(
                profile,
                page=int(self.request.GET.get("page") or 1),
                q=(self.request.GET.get("q") or "").strip(),
                category=(self.request.GET.get("category") or "").strip(),
                status_filter=(self.request.GET.get("status") or "").strip(),
                organization=(self.request.GET.get("organization") or "").strip(),
            )
        return context


class JobSeekerMessagesView(JobSeekerPortalMixin, TemplateView):
    template_name = "it/jobseeker/messages/index.html"
    sidebar_active_key = "dashboard"
    page_title = "Messages"
    page_description = "Recruiter notifications and selection alerts."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["messages_page"] = JobSeekerMessagesPortalService().list_messages(
            self.request.user, page=max(1, int(self.request.GET.get("page") or 1))
        )
        return context


class JobSeekerNotificationsView(_JobSeekerPageView):
    sidebar_active_key = "dashboard"
    page_title = "Notifications"
    page_description = "Your latest alerts and updates."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications, unread = JobSeekerDashboardService()._notifications(
            self.request.user
        )
        context["notifications"] = notifications
        context["unread_notification_count"] = unread
        return context


class JobSeekerJobDetailView(_JobSeekerPageView):
    sidebar_active_key = "browse_jobs"
    template_name = "it/jobseeker/job_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = get_object_or_404(
            JobPosting.objects.select_related("company", "company__logo_file"),
            pk=kwargs["job_id"],
            is_deleted=False,
        )
        JobPostingRepository().increment_view_count(job)
        context["job"] = job
        context["page_title"] = job.title
        context["page_description"] = job.company_name_snapshot or job.company.name
        return context


class JobSeekerApplicationDetailView(JobSeekerPortalMixin, TemplateView):
    sidebar_active_key = "applications"
    template_name = "it/jobseeker/applications/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile is None:
            return context
        detail = JobSeekerApplicationPortalService().get_detail(
            profile, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Application not found.")
        context["application_detail"] = detail
        context["page_title"] = detail.job_title
        context["page_description"] = detail.company_name
        return context


class JobSeekerApplyJobView(JobSeekerPortalMixin, View):
    """Apply to a published job posting."""

    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = self.get_profile()
        if profile is None:
            messages.error(request, "Complete your profile before applying.")
            return redirect(self.portal_url("jobseeker_profile"))

        try:
            job = get_object_or_404(JobPosting, pk=job_id, is_deleted=False)
            JobApplicationService().apply(
                job_posting=job,
                job_seeker=profile,
            )
            messages.success(request, "Application submitted successfully.")
            return redirect(self.portal_url("jobseeker_applications"))
        except Exception as exc:
            messages.error(request, str(exc))
            return redirect(self.portal_url("jobseeker_job_detail", job_id=job_id))


class JobSeekerSaveJobView(JobSeekerPortalMixin, View):
    """Save or unsave a job posting."""

    http_method_names = ["post"]

    def post(self, request, job_id):
        profile = self.get_profile()
        if profile is None:
            return redirect(self.portal_url("jobseeker_profile"))

        service = SavedJobService()
        try:
            result = service.toggle(profile, job_id)
        except ValueError as exc:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(exc)}, status=404)
            messages.error(request, str(exc))
            return redirect(
                request.POST.get("next") or self.portal_url("jobseeker_saved_jobs")
            )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "data": result.to_dict(), "is_saved": result.is_saved}
            )

        if result.is_saved:
            messages.success(request, result.message)
        else:
            messages.info(request, result.message)
        next_url = request.POST.get("next") or self.portal_url("jobseeker_saved_jobs")
        return redirect(next_url)


class JobSeekerNotificationReadView(JobSeekerPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient_domain="it",
            recipient_id=request.user.pk,
        )
        notification.mark_read()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("jobseeker_notifications"))


class JobSeekerNotificationsMarkAllReadView(JobSeekerPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        Notification.objects.filter(
            recipient_domain="it", recipient_id=request.user.pk, is_read=False
        ).update(is_read=True)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("jobseeker_notifications"))
