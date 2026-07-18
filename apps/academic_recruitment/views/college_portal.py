"""Institution (College) recruiter portal views."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView
from django.utils import timezone

from apps.accounts.models.college_user import CollegeUser
from apps.academic_recruitment.services.college_analytics_portal_service import (
    CollegeAnalyticsPortalService,
)
from apps.academic_recruitment.services.college_application_detail_portal_service import (
    CollegeApplicationDetailPortalService,
)
from apps.academic_recruitment.services.college_applications_portal_service import (
    CollegeApplicationsPortalService,
)
from apps.academic_recruitment.services.college_dashboard_portal_service import (
    CollegeDashboardPortalService,
)
from apps.academic_recruitment.services.college_interview_portal_service import (
    CollegeInterviewPortalService,
)
from apps.academic_recruitment.services.college_notifications_portal_service import (
    CollegeNotificationsPortalService,
)
from apps.academic_recruitment.services.college_profile_portal_service import (
    CollegeProfilePortalService,
)
from apps.academic_recruitment.services.college_settings_portal_service import (
    CollegeSettingsPortalService,
)
from apps.academic_recruitment.services.college_portal_helpers import (
    build_college_sidebar,
    initials_from_name,
    primary_institution_for_user,
)
from apps.academic_recruitment.services.college_vacancies_portal_service import (
    CollegeVacanciesPortalService,
)
from apps.academic_recruitment.services.college_vacancy_create_portal_service import (
    CollegeVacancyCreatePortalService,
)
from apps.authentication.services.identity_service import IdentityService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    ValidationException,
)
from apps.core.portal_header_config import INSTITUTION_RECRUITER_HEADER
from apps.faculty.services.faculty_vacancy_service import FacultyVacancyService
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.notifications.models import Notification


class CollegePortalMixin(LoginRequiredMixin):
    """Shared context for institution recruiter portal pages."""

    login_url = "/faculty/login/institution/"
    sidebar_active_key = "dashboard"
    page_title = ""
    page_description = ""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not isinstance(request.user, CollegeUser):
            other = WebJWTService.resolve_dashboard_url(request.user)
            return redirect(other)
        if request.user.is_authenticated and kwargs.get("user_uuid"):
            if not IdentityService.uuids_match(request.user.pk, kwargs.get("user_uuid")):
                other = WebJWTService.resolve_dashboard_url(request.user)
                return redirect(other)
        return super().dispatch(request, *args, **kwargs)

    def portal_url(self, view_name: str, **kwargs) -> str:
        return PortalURLService.college(self.request.user, view_name, **kwargs)

    def get_portal_header_context(self) -> dict:
        institution = primary_institution_for_user(self.request.user)
        display_name = (
            institution["name"]
            if institution
            else self.request.user.email.split("@")[0]
        )
        avatar_url = institution["logo_url"] if institution else None
        unread = Notification.objects.filter(
            recipient_domain="college", recipient_id=self.request.user.pk, is_read=False
        ).count()
        return {
            "header_user": {
                "display_name": display_name,
                "role_label": "Institution Recruiter",
                "initials": initials_from_name(
                    display_name, self.request.user.email[:2]
                ),
                "avatar_url": avatar_url,
                "profile_url": self.portal_url("college_profile"),
                "user_uuid": IdentityService.public_uuid(self.request.user),
            },
            "unread_notification_count": unread,
            "notifications_url": self.portal_url("college_notifications"),
            "messages_url": self.portal_url("college_messages"),
            "logout_url": reverse("logout"),
            "search_url": self.portal_url("college_vacancies"),
            "portal_header": INSTITUTION_RECRUITER_HEADER,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = primary_institution_for_user(self.request.user)
        
        is_profile_completed = False
        completion_state_global = None
        if institution:
            from apps.colleges.selectors.college_selector import CollegeMemberSelector
            from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
            membership = CollegeMemberSelector().primary_for_user(self.request.user)
            if membership:
                completion_state = CollegeProfileCompletionService().get_dashboard_state(membership.college, self.request.user)
                is_profile_completed = completion_state.percentage == 100
                completion_state_global = completion_state.to_dict()

        context.update(self.get_portal_header_context())
        context["is_profile_completed"] = is_profile_completed
        context["completion_state_global"] = completion_state_global
        context["sidebar"] = build_college_sidebar(
            self.sidebar_active_key, self.request.user
        )
        context["sidebar_profile"] = {
            "display_name": institution["name"]
            if institution
            else context["header_user"]["display_name"],
            "headline": institution["verification_label"]
            if institution
            else "Institution Recruiter",
        }
        context["institution_branding"] = institution
        context["portal_user_uuid"] = IdentityService.public_uuid(self.request.user)
        context["page_title"] = self.page_title
        context["page_description"] = self.page_description
        return context


class CollegeDashboardView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/dashboard/index.html"
    sidebar_active_key = "dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = CollegeDashboardPortalService().build(user=self.request.user)
        context["dashboard"] = dashboard
        context["insights_url"] = dashboard.get("urls", {}).get(
            "insights", self.portal_url("college_dashboard_insights_api")
        )
        return context


class CollegeVacanciesView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/vacancies/index.html"
    sidebar_active_key = "vacancies"
    page_title = "Manage Vacancies"
    page_description = "View, edit, and publish faculty vacancies."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        try:
            page = max(1, int(self.request.GET.get("page") or 1))
        except ValueError:
            page = 1
        context["vacancies_page"] = CollegeVacanciesPortalService().build(
            self.request.user, status_filter=status, q=q, page=page
        )
        context["status_filter"] = status
        context["search_query"] = q
        context["vacancy_created"] = self.request.GET.get("created") == "1"
        return context


class CollegeVacancyCreateView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/vacancies/create.html"
    sidebar_active_key = "post_vacancy"
    page_title = "Post Vacancy"
    page_description = "Create and publish a new faculty vacancy."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal_service = CollegeVacancyCreatePortalService()
        create_page = portal_service.build(self.request.user)
        context["create_page"] = create_page
        context.setdefault("form_errors", [])
        context.setdefault("form_data", {})
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        create_page = context["create_page"]
        
        # Enforce Profile Completion
        if create_page.institution:
            from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
            completion_state = CollegeProfileCompletionService().get_dashboard_state(
                create_page.institution.get("_college_obj") or CollegeVacancyCreatePortalService._get_college_obj(request.user),
                request.user
            )
            if completion_state.percentage < 100:
                context["completion_state"] = completion_state.to_dict()
                self.template_name = "academic/college/vacancies/restricted.html"
                return self.render_to_response(context)

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        college_id = CollegeVacancyCreatePortalService.primary_college_id(request.user)
        if not college_id:
            context = self.get_context_data()
            context["form_errors"] = [
                "Set up your institution profile before posting vacancies."
            ]
            context["form_data"] = request.POST
            return self.render_to_response(context)

        # Enforce Profile Completion
        college_obj = CollegeVacancyCreatePortalService._get_college_obj(request.user)
        if college_obj:
            from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
            completion_state = CollegeProfileCompletionService().get_dashboard_state(college_obj, request.user)
            if completion_state.percentage < 100:
                context = self.get_context_data()
                context["completion_state"] = completion_state.to_dict()
                self.template_name = "academic/college/vacancies/restricted.html"
                return self.render_to_response(context)

        parsed = CollegeVacancyCreatePortalService.parse_form(request.POST)
        if parsed["errors"]:
            context = self.get_context_data()
            context["form_errors"] = parsed["errors"]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)

        try:
            vacancy = FacultyVacancyService().create_vacancy(
                college_user=request.user,
                data={"college_id": college_id, **parsed["data"]},
            )
            from apps.faculty.services.vacancy_publication_service import FacultyPublicationService
            FacultyPublicationService().publish(vacancy=vacancy, college_user=request.user)
            messages.success(request, "🎉 Job Published Successfully! Your vacancy is now live and visible to faculty job seekers.")
            return redirect(f"{self.portal_url('college_vacancies')}")
        except (ValidationException, BusinessLogicException, ConflictException) as exc:
            context = self.get_context_data()
            context["form_errors"] = [str(exc)]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)


class CollegeVacancyEditView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/vacancies/edit.html"
    sidebar_active_key = "vacancies"
    page_title = "Edit Vacancy"
    page_description = "Update faculty vacancy details."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vacancy_id = self.kwargs.get("vacancy_id")
        vacancy = (
            FacultyVacancySelector()
            .for_college_user(self.request.user)
            .filter(pk=vacancy_id)
            .first()
        )
        if not vacancy:
            raise Http404("Vacancy not found.")
        pu = self.portal_url
        context["create_page"] = CollegeVacancyCreatePortalService().build(
            self.request.user
        )
        context["vacancy"] = vacancy
        context["serialized_vacancy"] = (
            CollegeVacanciesPortalService._serialize_vacancy(vacancy, pu, {})
        )
        context.setdefault("form_errors", [])
        context.setdefault("form_data", context["serialized_vacancy"])
        return context

    def post(self, request, *args, **kwargs):
        vacancy_id = self.kwargs.get("vacancy_id")
        vacancy = (
            FacultyVacancySelector()
            .for_college_user(request.user)
            .filter(pk=vacancy_id)
            .first()
        )
        if not vacancy:
            raise Http404("Vacancy not found.")
        parsed = CollegeVacancyCreatePortalService.parse_form(request.POST)
        if parsed["errors"]:
            context = self.get_context_data(**kwargs)
            context["form_errors"] = parsed["errors"]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)
        try:
            vacancy = FacultyVacancyService().update_vacancy(
                vacancy=vacancy, college_user=request.user, data=parsed["data"]
            )
            from apps.faculty.constants.enums import VacancyStatus
            if vacancy.status == VacancyStatus.DRAFT:
                from apps.faculty.services.vacancy_publication_service import FacultyPublicationService
                FacultyPublicationService().publish(vacancy=vacancy, college_user=request.user)
                messages.success(request, "🎉 Job Published Successfully! Your vacancy is now live and visible to faculty job seekers.")
            else:
                messages.success(request, "Vacancy updated successfully.")
            return redirect(f"{self.portal_url('college_vacancies')}")
        except (ValidationException, BusinessLogicException, ConflictException) as exc:
            context = self.get_context_data(**kwargs)
            context["form_errors"] = [str(exc)]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)


class CollegeApplicationsView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/applications/index.html"
    sidebar_active_key = "applications"
    page_title = "Applications"
    page_description = "Review and manage faculty applications."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        vacancy_id = (self.request.GET.get("vacancy_id") or "").strip()
        try:
            page = max(1, int(self.request.GET.get("page") or 1))
        except ValueError:
            page = 1
        sort = (self.request.GET.get("sort") or "newest").strip()
        page_ctx = CollegeApplicationsPortalService().build(
            self.request.user, q=q, status=status, vacancy_id=vacancy_id, page=page, sort=sort
        )
        context["applications_page"] = page_ctx

        # Mark all new application notifications as read
        Notification.objects.filter(
            recipient_domain="college",
            recipient_id=self.request.user.pk,
            event_type="NEW_FACULTY_APPLICATION",
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        filters = page_ctx.filters
        context["pagination_prev_query"] = (
            CollegeApplicationsPortalService.filters_query(
                page - 1 if page > 1 else 1, filters
            )
        )
        context["pagination_next_query"] = (
            CollegeApplicationsPortalService.filters_query(page + 1, filters)
        )
        return context


class CollegeInterviewsView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/interviews/index.html"
    sidebar_active_key = "interviews"
    page_title = "Interviews"
    page_description = "Schedule and track faculty interview rounds."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        try:
            page = max(1, int(self.request.GET.get("page") or 1))
        except ValueError:
            page = 1
        context["interviews_page"] = CollegeInterviewPortalService().build(
            self.request.user,
            page=page,
            q=q,
            status=status,
        )
        return context


class CollegeProfileView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/profile/index.html"
    sidebar_active_key = "profile"
    page_title = "Institution Profile"
    page_description = (
        "Manage your institution branding, contact details, and verification."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_page"] = CollegeProfilePortalService().build(self.request.user)
        return context


class CollegeStubPageView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/partials/stub_page.html"
    stub_icon = "bi-tools"
    stub_cta_url_name = "college_dashboard"
    stub_cta_label = "Back to Dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stub_page"] = {
            "title": self.page_title,
            "description": self.page_description,
            "message": getattr(
                self, "stub_message", "This section is being built. Check back soon."
            ),
            "icon": self.stub_icon,
            "cta_url": self.portal_url(self.stub_cta_url_name),
            "cta_label": self.stub_cta_label,
        }
        return context


class CollegeApplicationDetailView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/applications/detail.html"
    sidebar_active_key = "applications"
    page_title = "Application Detail"
    page_description = "Review faculty applicant profile and pipeline status."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        detail = CollegeApplicationDetailPortalService().get_detail(
            self.request.user, kwargs["application_id"]
        )
        if detail is None:
            raise Http404("Application not found.")
        context["application_detail"] = detail
        context["page_title"] = detail.candidate_name
        context["page_description"] = detail.vacancy_title
        return context


class CollegeAnalyticsView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/analytics/index.html"
    sidebar_active_key = "analytics"
    page_title = "Analytics"
    page_description = "Hiring metrics and faculty recruitment insights."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["analytics_page"] = CollegeAnalyticsPortalService().build(
            self.request.user
        )
        return context


class CollegeMessagesView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/messages/index.html"
    sidebar_active_key = "messages"
    page_title = "Messages"
    page_description = "Conversations with faculty applicants."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        state = (self.request.GET.get("state") or "all").strip().lower()
        if state not in {"all", "unread", "read"}:
            state = "all"
        context["messages_page"] = CollegeNotificationsPortalService().list_messages(
            self.request.user,
            page=max(1, int(self.request.GET.get("page") or 1)),
            state=state,
        )
        context["messages_filters"] = {"state": state}
        return context


class CollegeNotificationsView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/notifications/index.html"
    sidebar_active_key = "notifications"
    page_title = "Notifications"
    page_description = "Updates about applications, vacancies, and verification."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        state = (self.request.GET.get("state") or "all").strip().lower()
        if state not in {"all", "unread", "read"}:
            state = "all"
        event = (self.request.GET.get("event") or "").strip()
        context["notifications_page"] = (
            CollegeNotificationsPortalService().list_notifications(
                self.request.user,
                page=max(1, int(self.request.GET.get("page") or 1)),
                event=event,
                state=state,
            )
        )
        context["notifications_filters"] = {"state": state, "event": event}
        context["unread_notification_count"] = context[
            "notifications_page"
        ].unread_count
        return context


class CollegeSettingsView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/settings/index.html"
    sidebar_active_key = "settings"
    page_title = "Settings"
    page_description = "Account, security, and notification preferences."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal = CollegeSettingsPortalService()
        settings_ctx = portal.build(self.request.user, request=self.request)
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


class CollegeNotificationReadView(CollegePortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, notification_id, **kwargs):
        notification = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient_domain="college",
            recipient_id=request.user.pk,
        )
        notification.mark_read()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("college_notifications"))


class CollegeNotificationsMarkAllReadView(CollegePortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        Notification.objects.filter(
            recipient_domain="college", recipient_id=request.user.pk, is_read=False
        ).update(is_read=True)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("college_notifications"))


class CollegeShortlistedCandidatesView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/shortlisted/index.html"
    sidebar_active_key = "shortlisted"
    page_title = "Shortlisted Candidates"
    page_description = "Manage shortlisted candidates and schedule interviews."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        
        q = (self.request.GET.get("q") or "").strip()
        from django.core.paginator import Paginator
        from django.db.models import Q
        
        from apps.applications.models import FacultyApplication
        from apps.applications.selectors.application_selector import FacultyApplicationSelector
        from apps.applications.constants.faculty_enums import FacultyApplicationStatus
        qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .filter(
                status__in=[
                    FacultyApplicationStatus.SHORTLISTED,
                    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                    FacultyApplicationStatus.DEPARTMENT_REVIEW,
                    FacultyApplicationStatus.PRINCIPAL_REVIEW,
                    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                ]
            )
            .select_related(
                "vacancy",
                "professor",
                "professor__user",
                "professor__profile_photo",
                "professor__cv_file",
                "college",
            )
        )
        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(vacancy_title_snapshot__icontains=q)
                | Q(department__icontains=q)
            )

        paginator = Paginator(qs.order_by("-applied_at"), 20)
        page = max(1, int(self.request.GET.get("page") or 1))
        page_obj = paginator.get_page(page)

        service = CollegeApplicationsPortalService()
        serialized_apps = [service._serialize_app(app, pu) for app in page_obj.object_list]

        context["candidates"] = serialized_apps
        context["pagination"] = {
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
        context["q"] = q
        
        placeholder = "00000000-0000-0000-0000-000000000000"
        context["api_urls"] = {
            "schedule_template": pu("college_interview_schedule_api", application_id=placeholder),
            "complete_template": pu("college_interview_complete_api", application_id=placeholder),
            "status_template": pu("college_application_status_api", application_id=placeholder),
            "notes_template": pu("college_application_notes_api", application_id=placeholder),
        }
        return context


class CollegeSelectedCandidatesView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/selected/index.html"
    sidebar_active_key = "selected"
    page_title = "Selected Candidates"
    page_description = "Track selection progression, offer acceptances, joining, and invoices."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        
        q = (self.request.GET.get("q") or "").strip()
        from django.core.paginator import Paginator
        from django.db.models import Q
        
        from apps.applications.models import FacultyApplication, PlacementDetails
        from apps.applications.selectors.application_selector import FacultyApplicationSelector
        from apps.invoices.models import Invoice
        
        qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .filter(status__in=["selected", "joining_in_progress"])
            .select_related(
                "vacancy",
                "professor",
                "professor__user",
                "professor__profile_photo",
                "professor__cv_file",
                "college",
            )
        )
        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(vacancy_title_snapshot__icontains=q)
                | Q(department__icontains=q)
            )

        paginator = Paginator(qs.order_by("-status_changed_at"), 20)
        page = max(1, int(self.request.GET.get("page") or 1))
        page_obj = paginator.get_page(page)

        service = CollegeApplicationsPortalService()
        candidates = []
        for app in page_obj.object_list:
            app_data = service._serialize_app(app, pu)
            placement = PlacementDetails.objects.filter(application_id=app.pk).first()
            from apps.billing.models.fee import PlacementFee
            fee = PlacementFee.objects.filter(entity_id=app.pk, is_deleted=False).first()
            invoice = Invoice.objects.filter(placement_fee_id=fee.pk, is_deleted=False).first() if fee else None
            
            candidates.append({
                "app": app_data,
                "placement": placement,
                "invoice": invoice,
                "vacancy": app.vacancy,
            })

        context["candidates"] = candidates
        context["pagination"] = {
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
        context["q"] = q
        return context

    def post(self, request, *args, **kwargs):
        from apps.applications.services.recruitment_workflow_service import RecruitmentWorkflowService
        action = request.POST.get("action")
        application_id = request.POST.get("application_id")
        
        if not application_id:
            return JsonResponse({"success": False, "error": "Application ID is required."}, status=400)
            
        try:
            workflow_service = RecruitmentWorkflowService()
            if action == "update_joining":
                data = {
                    "expected_joining_date": request.POST.get("expected_joining_date") or None,
                    "offered_designation": request.POST.get("offered_designation", ""),
                    "department": request.POST.get("department", ""),
                    "work_location": request.POST.get("work_location", ""),
                    "employment_type": request.POST.get("employment_type", ""),
                    "agreed_salary": request.POST.get("agreed_salary") or None,
                    "offer_reference_number": request.POST.get("offer_reference_number", ""),
                    "joining_notes": request.POST.get("joining_notes", ""),
                }
                workflow_service.update_joining_details("faculty", application_id, request.user, data)
                messages.success(request, "Joining details updated successfully.")
            elif action == "confirm_joined":
                data = {
                    "actual_joining_date": request.POST.get("actual_joining_date") or None,
                    "employee_id": request.POST.get("employee_id", ""),
                    "notes": request.POST.get("notes", ""),
                }
                workflow_service.confirm_joined("faculty", application_id, request.user, data)
                messages.success(request, "Candidate marked as joined successfully. 90-day guarantee started.")
            else:
                return JsonResponse({"success": False, "error": "Invalid action."}, status=400)
                
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect(request.path)
        except Exception as e:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)
            messages.error(request, f"Error: {str(e)}")
            return redirect(request.path)


class CollegeJoinedCandidatesView(CollegePortalMixin, TemplateView):
    template_name = "academic/college/joined/index.html"
    sidebar_active_key = "joined"
    page_title = "Joined Candidates"
    page_description = "Monitor placement guarantee status and process refund/replacement claims."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        
        q = (self.request.GET.get("q") or "").strip()
        from django.core.paginator import Paginator
        from django.db.models import Q
        
        from apps.applications.models import FacultyApplication, PlacementDetails
        from apps.applications.selectors.application_selector import FacultyApplicationSelector
        from apps.invoices.models import Invoice
        from apps.guarantee_claims.models import PlacementGuarantee, PlacementClaim
        from apps.guarantee_claims.constants.enums import GuaranteeStatus
        
        qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .filter(status="joined")
            .select_related(
                "vacancy",
                "professor",
                "professor__user",
                "professor__profile_photo",
                "professor__cv_file",
                "college",
            )
        )
        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(vacancy_title_snapshot__icontains=q)
                | Q(department__icontains=q)
            )

        paginator = Paginator(qs.order_by("-status_changed_at"), 20)
        page = max(1, int(self.request.GET.get("page") or 1))
        page_obj = paginator.get_page(page)

        service = CollegeApplicationsPortalService()
        candidates = []
        for app in page_obj.object_list:
            app_data = service._serialize_app(app, pu)
            placement = PlacementDetails.objects.filter(application_id=app.pk).first()
            from apps.billing.models.fee import PlacementFee
            fee = PlacementFee.objects.filter(entity_id=app.pk, is_deleted=False).first()
            invoice = Invoice.objects.filter(placement_fee_id=fee.pk, is_deleted=False).first() if fee else None
            
            guarantee = None
            days_since_joining = None
            claim_eligible = False
            active_claim = None
            
            if placement and placement.actual_joining_date:
                days_since_joining = (timezone.now().date() - placement.actual_joining_date).days
                if invoice:
                    guarantee = PlacementGuarantee.objects.filter(invoice_id=invoice.pk, is_deleted=False).first()
                
                if days_since_joining <= 90:
                    active_claim = PlacementClaim.objects.filter(
                        application_id=app.pk,
                        is_deleted=False
                    ).exclude(status__in=["rejected", "closed", "refund_failed"]).first()
                    if not active_claim:
                        claim_eligible = True
            
            candidates.append({
                "app": app_data,
                "placement": placement,
                "invoice": invoice,
                "guarantee": guarantee,
                "days_since_joining": days_since_joining,
                "claim_eligible": claim_eligible,
                "active_claim": active_claim,
            })

        context["candidates"] = candidates
        context["pagination"] = {
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
        context["q"] = q
        return context

    def post(self, request, *args, **kwargs):
        from apps.guarantee_claims.services.placement_claim_service import PlacementClaimService
        from apps.applications.models import FacultyApplication
        
        application_id = request.POST.get("application_id")
        claim_reason = request.POST.get("claim_reason")
        incident_date = request.POST.get("incident_date")
        claim_description = request.POST.get("claim_description")
        claim_type = request.POST.get("claim_type", "refund")
        
        if not application_id or not claim_reason or not incident_date or not claim_description:
            return JsonResponse({"success": False, "error": "All fields are required."}, status=400)
            
        try:
            application = FacultyApplication.objects.get(pk=application_id)
            data = {
                "claim_reason": claim_reason,
                "incident_date": incident_date,
                "claim_description": claim_description,
                "claim_type": claim_type,
            }
            PlacementClaimService().submit_claim(application, request.user.pk, data)
            messages.success(request, "Refund/Replacement claim submitted successfully. It is now under super admin review.")
            
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect(request.path)
        except Exception as e:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)
            messages.error(request, f"Error submitting claim: {str(e)}")
            return redirect(request.path)
