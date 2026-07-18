"""Professor (Faculty Job Seeker) portal views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.generic import TemplateView

from apps.core.exceptions.domain_exceptions import ResumeRequiredException
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_application_portal_service import (
    ProfessorApplicationPortalService,
)
from apps.academic_recruitment.services.professor_dashboard_portal_service import (
    ProfessorDashboardPortalService,
)
from apps.academic_recruitment.services.professor_interview_portal_service import (
    ProfessorInterviewPortalService,
)
from apps.academic_recruitment.services.professor_resume_portal_service import (
    ProfessorResumePortalService,
)
from apps.academic_recruitment.services.professor_tracker_portal_service import (
    ProfessorTrackerPortalService,
)
from apps.academic_recruitment.services.professor_notifications_portal_service import (
    ProfessorNotificationsPortalService,
)
from apps.academic_recruitment.services.professor_browse_portal_service import (
    ProfessorBrowsePortalService,
)
from apps.academic_recruitment.services.professor_profile_manage_service import (
    ProfessorProfileManageService,
)
from apps.academic_recruitment.services.professor_research_portal_service import (
    ProfessorResearchPortalService,
)
from apps.academic_recruitment.services.professor_certificate_portal_service import (
    ProfessorCertificatePortalService,
)
from apps.academic_recruitment.services.professor_settings_portal_service import (
    ProfessorSettingsPortalService,
)
from apps.academic_recruitment.services.professor_vacancy_portal_service import (
    ProfessorVacancyPortalService,
)
from apps.academic_recruitment.services.professor_portal_helpers import (
    build_professor_sidebar,
    initials_from_name,
    media_url,
)
from apps.accounts.models.professor_user import ProfessorUser
from apps.applications.models import FacultyApplication
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.authentication.services.identity_service import IdentityService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_selector import PublicFacultyVacancySelector
from apps.faculty.services.saved_vacancy_service import SavedVacancyService
from apps.core.portal_header_config import FACULTY_JOB_SEEKER_HEADER
from apps.notifications.models import Notification


class ProfessorPortalMixin(LoginRequiredMixin):
    """Shared context for professor portal pages."""

    login_url = "/faculty/login/professor/"
    sidebar_active_key = "dashboard"
    page_title = ""
    page_description = ""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not isinstance(
            request.user, ProfessorUser
        ):
            other = WebJWTService.resolve_dashboard_url(request.user)
            return redirect(other)
        if request.user.is_authenticated and kwargs.get("user_uuid"):
            if not IdentityService.uuids_match(request.user.pk, kwargs.get("user_uuid")):
                other = WebJWTService.resolve_dashboard_url(request.user)
                return redirect(other)
        return super().dispatch(request, *args, **kwargs)

    def portal_url(self, view_name: str, **kwargs) -> str:
        return PortalURLService.professor(self.request.user, view_name, **kwargs)

    def get_profile(self) -> ProfessorProfile | None:
        return (
            ProfessorProfile.objects.filter(user=self.request.user, is_deleted=False)
            .select_related("profile_photo", "cv_file", "user")
            .prefetch_related("qualifications", "departments__department")
            .first()
        )

    def get_portal_header_context(self, profile: ProfessorProfile | None) -> dict:
        display_name = (
            profile.full_name if profile else self.request.user.email.split("@")[0]
        )
        avatar_url = (
            media_url(profile.profile_photo)
            if profile and profile.profile_photo
            else None
        )
        notifications, unread = ProfessorDashboardPortalService()._notifications(
            self.request.user
        )
        from apps.notifications.services.application_status_notification_service import ApplicationStatusNotificationService
        unread_tracker = ApplicationStatusNotificationService.get_unread_tracker_count(
            self.request.user.pk, "professor"
        )
        return {
            "header_user": {
                "display_name": display_name,
                "role_label": "Faculty Job Seeker",
                "initials": initials_from_name(
                    display_name, self.request.user.email[:2]
                ),
                "avatar_url": avatar_url,
                "profile_url": self.portal_url("professor_profile"),
                "user_uuid": IdentityService.public_uuid(self.request.user),
            },
            "header_notifications": notifications,
            "unread_notification_count": unread,
            "unread_tracker_count": unread_tracker,
            "messages_url": self.portal_url("professor_messages"),
            "notifications_url": self.portal_url("professor_notifications"),
            "logout_url": reverse("logout"),
            "search_url": self.portal_url("professor_browse_jobs"),
            "portal_header": FACULTY_JOB_SEEKER_HEADER,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        context["professor_profile"] = profile
        context.update(self.get_portal_header_context(profile))
        context["sidebar"] = build_professor_sidebar(
            self.sidebar_active_key, self.request.user
        )
        context["sidebar_profile"] = {
            "display_name": profile.full_name
            if profile
            else context["header_user"]["display_name"],
            "headline": (
                profile.current_designation
                if profile and profile.current_designation
                else (profile.specialization if profile else "Faculty Job Seeker")
            ),
        }
        context["portal_user_uuid"] = IdentityService.public_uuid(self.request.user)
        context["page_title"] = self.page_title
        context["page_description"] = self.page_description
        context["saved_jobs_count"] = (
            SavedVacancyService().count(profile) if profile else 0
        )
        return context


class ProfessorBrowseJobsView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/browse_jobs/index.html"
    sidebar_active_key = "browse_jobs"
    page_title = "Job Search"
    page_description = "Browse published faculty vacancies and apply directly."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        context["browse_page"] = (
            ProfessorBrowsePortalService()
            .list_vacancies(
                profile,
                page=max(1, int(self.request.GET.get("page") or 1)),
                q=(self.request.GET.get("q") or "").strip(),
                department=(self.request.GET.get("department") or "").strip(),
                city=(self.request.GET.get("city") or "").strip(),
            )
            .to_template_dict()
        )
        return context


class ProfessorVacancyDetailView(ProfessorPortalMixin, TemplateView):
    sidebar_active_key = "browse_jobs"
    template_name = "academic/professor/vacancy_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vacancy = PublicFacultyVacancySelector().get_published(kwargs["vacancy_id"])
        if not vacancy:
            raise Http404("Vacancy not found.")
        profile = self.get_profile()
        detail = ProfessorVacancyPortalService().build_detail(profile, vacancy)
        context["vacancy_page"] = detail.to_template_dict()
        context["page_title"] = detail.title
        context["page_description"] = f"{detail.institution_name} • {detail.location}"
        return context


class ProfessorDashboardView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/dashboard/index.html"
    sidebar_active_key = "dashboard"

    def get_context_data(self, **kwargs):
        context = ProfessorPortalMixin.get_context_data(self, **kwargs)
        profile = self.get_profile()
        dashboard = ProfessorDashboardPortalService().build(
            user=self.request.user, profile=profile
        )
        context["dashboard"] = dashboard
        
        has_selected_application = FacultyApplication.objects.filter(
            professor=profile,
            status__in=[FacultyApplicationStatus.SELECTED, FacultyApplicationStatus.OFFER_ACCEPTED]
        ).exists() if profile else False
        
        # Only show celebration once per session to avoid annoying the user on every reload
        if has_selected_application and not self.request.session.get('selection_celebrated'):
            context["show_selection_celebration"] = True
            self.request.session['selection_celebrated'] = True
        else:
            context["show_selection_celebration"] = False
        
        context["dashboard_json"] = {
            "saved_toggle_url": self.portal_url("professor_saved_job_toggle_api"),
            "saved_status_url": self.portal_url("professor_saved_vacancy_status_api"),
            "insights_url": self.portal_url("professor_dashboard_insights_api"),
            "notifications_mark_all_url": self.portal_url(
                "professor_notifications_mark_all_read"
            ),
        }
        return context


class ProfessorApplicationsView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/applications/index.html"
    sidebar_active_key = "applications"
    page_title = "Applications"
    page_description = "Track every faculty application in your pipeline."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["applications_page"] = (
                ProfessorApplicationPortalService().list_applications(
                    profile,
                    page=max(1, int(self.request.GET.get("page") or 1)),
                    status=(self.request.GET.get("status") or "").strip(),
                    q=(self.request.GET.get("q") or "").strip(),
                    active_only=self.request.GET.get("active") == "1",
                    interview_only=self.request.GET.get("interview") == "1",
                    offer_only=self.request.GET.get("offer") == "1",
                    rejected_only=self.request.GET.get("rejected") == "1",
                )
            )
        return context


class ProfessorSavedJobsView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/saved_jobs/index.html"
    sidebar_active_key = "saved_jobs"
    page_title = "Saved Jobs"
    page_description = "Faculty positions you have bookmarked for later."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["saved_jobs_page"] = SavedVacancyService().list_saved(
                profile, page=max(1, int(self.request.GET.get("page") or 1))
            )
        return context


class ProfessorTrackerView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/tracker/index.html"
    sidebar_active_key = "tracker"
    page_title = "Career Tracker"
    page_description = (
        "Monitor faculty applications, institution actions, and career milestones."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()

        # Mark all tracker notifications as read
        from apps.notifications.models.notification import Notification
        from django.utils import timezone
        Notification.objects.filter(
            recipient_id=self.request.user.pk,
            recipient_domain="professor",
            event_type="application.status_changed",
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        context["unread_tracker_count"] = 0

        if profile:
            context["tracker"] = ProfessorTrackerPortalService().build(
                profile,
                q=(self.request.GET.get("q") or "").strip(),
                status=(self.request.GET.get("status") or "").strip(),
                company=(self.request.GET.get("company") or "").strip(),
                activity_page=max(1, int(self.request.GET.get("page") or 1)),
            )
        return context


class ProfessorResumeView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/resume/index.html"
    sidebar_active_key = "resume"
    page_title = "Resume / CV"
    page_description = "Upload, preview, and manage your faculty CV."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["resume_page"] = ProfessorResumePortalService().build(profile)
        return context


class ProfessorCertificatesView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/certificates/index.html"
    sidebar_active_key = "certificates"
    page_title = "Certificates"
    page_description = "Manage your credentials and certifications."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["cert_page"] = ProfessorCertificatePortalService().build(
                profile,
                page=int(self.request.GET.get("page") or 1),
                q=(self.request.GET.get("q") or "").strip(),
                category=(self.request.GET.get("category") or "").strip(),
                status_filter=(self.request.GET.get("status") or "").strip(),
                organization=(self.request.GET.get("organization") or "").strip(),
            )
        return context


class ProfessorInterviewDetailView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/interviews/detail.html"
    sidebar_active_key = "interviews"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile is None:
            return context
        detail = ProfessorInterviewPortalService().get_detail(
            profile, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Interview not found.")
        context["interview"] = detail
        context["page_title"] = detail.job_title
        context["page_description"] = detail.company_name
        return context


class ProfessorInterviewPrintView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/interviews/print.html"
    sidebar_active_key = "interviews"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile is None:
            return context
        detail = ProfessorInterviewPortalService().get_detail(
            profile, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Interview not found.")
        context["interview"] = detail
        return context


class ProfessorInterviewsView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/interviews/index.html"
    sidebar_active_key = "interviews"
    page_title = "Interviews"
    page_description = "Manage interview invitations and schedules."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["interviews_page"] = (
                ProfessorInterviewPortalService().list_interviews(
                    profile,
                    page=max(1, int(self.request.GET.get("page") or 1)),
                    q=(self.request.GET.get("q") or "").strip(),
                    status_filter=(self.request.GET.get("status") or "").strip(),
                )
            )
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ProfessorProfileView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/profile/index.html"
    sidebar_active_key = "profile"
    page_title = "My Profile"
    page_description = "Manage your academic profile, qualifications, and research."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            page = ProfessorProfileManageService().build_page_context(profile)
            context["profile_page"] = page.to_template_dict()
        return context


class ProfessorResearchView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/research/index.html"
    sidebar_active_key = "research"
    page_title = "Research & Publications"
    page_description = "Showcase your research output and publications."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            page = ProfessorResearchPortalService().build(profile)
            context["research_page"] = {
                "publications_count": page.publications_count,
                "research_interests": page.research_interests,
                "specialization": page.specialization,
                "qualifications": page.qualifications,
                "profile_edit_url": page.profile_edit_url,
                "has_research": page.has_research,
            }
        return context


class ProfessorSettingsView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/settings/index.html"
    sidebar_active_key = "settings"
    page_title = "Settings"
    page_description = (
        "Account, password, notifications, privacy, sessions, and security."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            portal = ProfessorSettingsPortalService()
            settings_ctx = portal.build(profile, request=self.request)
            context["settings_page"] = {
                "account": settings_ctx.account,
                "notifications": settings_ctx.notifications,
                "privacy": settings_ctx.privacy,
                "security": settings_ctx.security,
                "connected_accounts": settings_ctx.connected_accounts,
                "sessions": settings_ctx.sessions,
                "audit_log": settings_ctx.audit_log,
                "api_urls": settings_ctx.api_urls,
            }
            context["notification_toggles"] = portal.notification_toggles(
                settings_ctx.notifications
            )
            context["privacy_toggles"] = portal.privacy_toggles(settings_ctx.privacy)
        return context


class ProfessorMessagesView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/messages/index.html"
    sidebar_active_key = "dashboard"
    page_title = "Messages"
    page_description = "Recruiter and institution conversations."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["messages_page"] = ProfessorNotificationsPortalService().list_messages(
            self.request.user, page=max(1, int(self.request.GET.get("page") or 1))
        )
        return context


class ProfessorNotificationsView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/notifications/index.html"
    sidebar_active_key = "dashboard"
    page_title = "Notifications"
    page_description = "Your latest alerts and updates."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notifications_page"] = (
            ProfessorNotificationsPortalService().list_notifications(
                self.request.user, page=max(1, int(self.request.GET.get("page") or 1))
            )
        )
        context["unread_notification_count"] = context[
            "notifications_page"
        ].unread_count
        return context


class ProfessorApplicationDetailView(ProfessorPortalMixin, TemplateView):
    template_name = "academic/professor/applications/detail.html"
    sidebar_active_key = "applications"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile is None:
            return context
        detail = ProfessorApplicationPortalService().get_detail(
            profile, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Application not found.")
        context["application_detail"] = detail
        context["page_title"] = detail.job_title
        context["page_description"] = detail.institution_name
        return context


class ProfessorApplyVacancyView(ProfessorPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, vacancy_id, **kwargs):
        profile = self.get_profile()
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if profile is None:
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Complete your profile before applying.",
                    },
                    status=400,
                )
            messages.error(request, "Complete your profile before applying.")
            return redirect(self.portal_url("professor_profile"))

        try:
            vacancy = get_object_or_404(FacultyVacancy, pk=vacancy_id, is_deleted=False)
            
            from apps.academic_recruitment.services.faculty_application_eligibility_service import FacultyApplicationEligibilityService
            eligibility = FacultyApplicationEligibilityService().check(profile, vacancy)
            if not eligibility.eligible:
                if is_ajax:
                    return JsonResponse(
                        {"success": False, "error": eligibility.message}, status=400
                    )
                messages.error(request, eligibility.message)
                return redirect(self.portal_url("professor_profile"))

            cover_letter = request.POST.get("cover_letter", "").strip()

            application = FacultyApplicationService().apply(
                vacancy=vacancy, professor=profile, cover_letter=cover_letter
            )

            if is_ajax:
                detail_url = self.portal_url("professor_application_detail", application_id=application.pk)
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Application submitted successfully.",
                        "redirect_url": self.portal_url("professor_applications"),
                        "application_detail_url": detail_url,
                    }
                )
            messages.success(request, "Application submitted successfully.")
            next_url = request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(
                self.portal_url(
                    "professor_application_detail", application_id=application.pk
                )
            )
        except ResumeRequiredException as exc:
            if is_ajax:
                return JsonResponse(
                    {"success": False, "code": "RESUME_REQUIRED", "message": str(exc)},
                    status=400,
                )
            messages.error(request, str(exc))
            next_url = request.POST.get("next") or self.portal_url(
                "professor_vacancy_detail", vacancy_id=vacancy_id
            )
            return redirect(f"{self.portal_url('professor_resume')}?next={next_url}")
        except Exception as exc:
            if is_ajax:
                return JsonResponse({"success": False, "error": str(exc)}, status=400)
            messages.error(request, str(exc))
            next_url = request.POST.get("next") or self.portal_url(
                "professor_vacancy_detail", vacancy_id=vacancy_id
            )
            return redirect(next_url)


class ProfessorApplicationWithdrawView(ProfessorPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, application_id, **kwargs):
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("Application withdrawal is disabled.")


class ProfessorSaveVacancyView(ProfessorPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, vacancy_id, **kwargs):
        profile = self.get_profile()
        if profile is None:
            return redirect(self.portal_url("professor_profile"))

        service = SavedVacancyService()
        try:
            result = service.toggle(profile, vacancy_id)
        except ValueError as exc:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(exc)}, status=404)
            messages.error(request, str(exc))
            return redirect(
                request.POST.get("next") or self.portal_url("professor_saved_jobs")
            )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "data": result.to_dict(), "is_saved": result.is_saved}
            )

        if result.is_saved:
            messages.success(request, result.message)
        else:
            messages.info(request, result.message)
        return redirect(
            request.POST.get("next") or self.portal_url("professor_saved_jobs")
        )


@method_decorator(csrf_protect, name="dispatch")
class ProfessorSavedJobToggleAPIView(ProfessorPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, vacancy_id=None, **kwargs):
        profile = self.get_profile()
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        vid = vacancy_id or request.POST.get("vacancy_id")
        if not vid:
            return JsonResponse(
                {"success": False, "error": "vacancy_id is required."}, status=400
            )

        try:
            result = SavedVacancyService().toggle(profile, vid)
            return JsonResponse({"success": True, "data": result.to_dict()})
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=404)
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


class ProfessorNotificationReadView(ProfessorPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, notification_id, **kwargs):
        notification = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient_domain="professor",
            recipient_id=request.user.pk,
        )
        notification.mark_read()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("professor_notifications"))


class ProfessorNotificationsMarkAllReadView(ProfessorPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        Notification.objects.filter(
            recipient_domain="professor", recipient_id=request.user.pk, is_read=False
        ).update(is_read=True)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("professor_notifications"))
