"""Recruiter portal views — UUID-scoped dashboard and role-protected pages."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.companies.services.company_service import JobPostingService
from apps.jobs.selectors.job_selector import JobPostingSelector
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ValidationException,
)

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.services.identity_service import IdentityService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    initials_from_name,
    media_url,
)
from apps.it_recruitment.services.recruiter_portal_helpers import (
    build_recruiter_sidebar_nav,
    primary_company_for_recruiter,
)
from apps.it_recruitment.services.recruiter_analytics_portal_service import (
    RecruiterAnalyticsPortalService,
)
from apps.it_recruitment.services.recruiter_candidates_portal_service import (
    RecruiterCandidatesPortalService,
)
from apps.it_recruitment.services.recruiter_dashboard_service import (
    RecruiterDashboardService,
)
from apps.it_recruitment.services.recruiter_interview_portal_service import (
    RecruiterInterviewPortalService,
)
from apps.it_recruitment.services.recruiter_jobs_portal_service import (
    RecruiterJobsPortalService,
)
from apps.it_recruitment.services.recruiter_messages_portal_service import (
    RecruiterMessagesPortalService,
)
from apps.it_recruitment.services.recruiter_notifications_portal_service import (
    RecruiterNotificationsPortalService,
)
from apps.it_recruitment.services.recruiter_profile_portal_service import (
    RecruiterProfilePortalService,
)
from apps.it_recruitment.services.recruiter_candidate_marketplace_service import (
    RecruiterCandidateMarketplaceService,
)
from apps.it_recruitment.services.recruiter_job_create_portal_service import (
    RecruiterJobCreatePortalService,
)
from apps.it_recruitment.services.recruiter_saved_candidates_portal_service import (
    RecruiterSavedCandidatesPortalService,
)
from apps.notifications.models import Notification


class RecruiterPortalMixin(LoginRequiredMixin):
    """Shared context for all recruiter portal pages."""

    login_url = "/it/login/recruiter/"
    required_role = ITUserRoleType.RECRUITER
    sidebar_active_key = "dashboard"
    page_title = ""
    page_description = ""

    def portal_url(self, view_name: str, **kwargs) -> str:
        return PortalURLService.recruiter(self.request.user, view_name, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and not RoleAssignmentService().user_has_it_role(
                request.user, self.required_role
            )
        ):
            return redirect(PortalURLService.dashboard_for_user(request.user))
        if request.user.is_authenticated and kwargs.get("user_uuid"):
            from apps.authentication.services.identity_service import IdentityService
            if not IdentityService.uuids_match(request.user.pk, kwargs.get("user_uuid")):
                return redirect(PortalURLService.dashboard_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_profile(self) -> RecruiterProfile | None:
        return (
            RecruiterProfile.objects.filter(user=self.request.user, is_deleted=False)
            .select_related("profile_image")
            .first()
        )

    def get_portal_header_context(self, profile: RecruiterProfile | None) -> dict:
        display_name = (
            profile.full_name if profile else self.request.user.email.split("@")[0]
        )
        avatar_url = (
            media_url(profile.profile_image)
            if profile and profile.profile_image
            else None
        )
        unread = Notification.objects.filter(
            recipient_domain="it", recipient_id=self.request.user.pk, is_read=False
        ).count()
        return {
            "header_user": {
                "display_name": display_name,
                "role_label": "Recruiter",
                "initials": initials_from_name(
                    display_name, self.request.user.email[:2]
                ),
                "avatar_url": avatar_url,
                "profile_url": PortalURLService.recruiter(
                    self.request.user, "recruiter_profile"
                ),
                "user_uuid": IdentityService.public_uuid(self.request.user),
            },
            "unread_notification_count": unread,
            "notifications_url": PortalURLService.recruiter(
                self.request.user, "recruiter_notifications"
            ),
            "messages_url": PortalURLService.recruiter(
                self.request.user, "recruiter_messages"
            ),
            "logout_url": reverse("logout"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        context.update(self.get_portal_header_context(profile))
        context["sidebar"] = build_recruiter_sidebar_nav(
            self.sidebar_active_key, self.request.user
        )
        context["company_branding"] = primary_company_for_recruiter(profile)
        context["portal_user_uuid"] = IdentityService.public_uuid(self.request.user)
        context["page_title"] = self.page_title
        context["page_description"] = self.page_description
        return context


class _RecruiterPageView(RecruiterPortalMixin, TemplateView):
    """Inner portal page using the recruiter dashboard shell."""

    template_name = "it/recruiter/portal_page.html"


class RecruiterDashboardView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/dashboard/index.html"
    sidebar_active_key = "dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["dashboard"] = RecruiterDashboardService().build(profile)
        return context


class RecruiterInterviewsView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/interviews/index.html"
    sidebar_active_key = "interviews"
    page_title = "Interviews"
    page_description = "Manage scheduled interviews and candidate meetings."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            try:
                page = max(1, int(self.request.GET.get("page") or 1))
            except ValueError:
                page = 1
            context["interviews_page"] = RecruiterInterviewPortalService().build(
                profile,
                when=(self.request.GET.get("when") or "").strip(),
                q=(self.request.GET.get("q") or "").strip(),
                status=(self.request.GET.get("status") or "").strip(),
                job_id=(self.request.GET.get("job_id") or "").strip(),
                mode=(self.request.GET.get("mode") or "").strip(),
                date_from=(self.request.GET.get("date_from") or "").strip(),
                date_to=(self.request.GET.get("date_to") or "").strip(),
                page=page,
            )
            context["when_filter"] = (self.request.GET.get("when") or "").strip()
        return context


class RecruiterAnalyticsView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/analytics/index.html"
    sidebar_active_key = "analytics"
    page_title = "Analytics"
    page_description = "Hiring funnel, job performance, and candidate source insights."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["analytics_page"] = RecruiterAnalyticsPortalService().build(profile)
            context["dashboard"] = RecruiterDashboardService().build(profile)
        return context


class RecruiterProfileView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/profile/index.html"
    sidebar_active_key = "profile"
    page_title = "Company Profile"
    page_description = "Manage your recruiter profile and company information."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["profile_page"] = RecruiterProfilePortalService().build(profile)
        return context


class RecruiterJobsView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/jobs/index.html"
    sidebar_active_key = "jobs"
    page_title = "Posted Jobs"
    page_description = "Create, publish, and manage your job postings."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            status = (self.request.GET.get("status") or "").strip()
            q = (self.request.GET.get("q") or "").strip()
            try:
                page = max(1, int(self.request.GET.get("page") or 1))
            except ValueError:
                page = 1
            context["jobs_page"] = RecruiterJobsPortalService().build(
                profile, status_filter=status, q=q, page=page
            )
            context["status_filter"] = status
            context["search_query"] = q
            context["job_created"] = self.request.GET.get("created") == "1"
            if context.get("jobs_page"):
                context["candidates_status_options"] = context[
                    "jobs_page"
                ].application_status_options
        return context


class RecruiterJobCreateView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/jobs/create.html"
    sidebar_active_key = "post_job"
    page_title = "Create Job"
    page_description = "Post a new IT role and start receiving applications."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["create_page"] = RecruiterJobCreatePortalService().build(profile)
        context.setdefault("form_errors", [])
        context.setdefault("form_data", {})
        return context

    def post(self, request, *args, **kwargs):
        profile = self.get_profile()
        if not profile:
            return redirect(self.portal_url("recruiter_dashboard"))

        membership = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .select_related("company")
            .order_by("-is_primary", "-created_at")
            .first()
        )
        if not membership:
            context = self.get_context_data()
            context["form_errors"] = ["Create a company profile before posting jobs."]
            context["form_data"] = request.POST
            return self.render_to_response(context)

        parsed = RecruiterJobCreatePortalService.parse_form(request.POST)
        if parsed["errors"]:
            context = self.get_context_data()
            context["form_errors"] = parsed["errors"]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)

        try:
            JobPostingService().create_published_job(
                company=membership.company,
                recruiter=profile,
                data=parsed["data"],
            )
            messages.success(request, "✅ Your job has been published successfully and is now live on the marketplace.")
            return redirect(f"{self.portal_url('recruiter_jobs')}?published=1")
        except (ValidationException, BusinessLogicException) as exc:
            context = self.get_context_data()
            context["form_errors"] = [str(exc)]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)


class RecruiterJobEditView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/jobs/edit.html"
    sidebar_active_key = "manage_jobs"
    page_title = "Edit Job"
    page_description = "Update job details, salary range, and requirements."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        job_id = self.kwargs.get("job_id")
        job = JobPostingSelector().for_recruiter(profile).filter(pk=job_id).first()
        if not job:
            raise Http404("Job not found or you do not have permission to edit it.")
        if profile:
            context["create_page"] = RecruiterJobCreatePortalService().build(profile)
        from apps.authentication.services.portal_url_service import PortalURLService

        pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
        context["job"] = job
        context["serialized_job"] = RecruiterJobsPortalService._serialize_job(job, pu)
        context.setdefault("form_errors", [])
        context.setdefault("form_data", context["serialized_job"].get("raw", {}))
        return context

    def post(self, request, *args, **kwargs):
        profile = self.get_profile()
        if not profile:
            return redirect(self.portal_url("recruiter_dashboard"))
        job_id = self.kwargs.get("job_id")
        job = JobPostingSelector().for_recruiter(profile).filter(pk=job_id).first()
        if not job:
            raise Http404("Job not found.")
        parsed = RecruiterJobCreatePortalService.parse_form(request.POST)
        if parsed["errors"]:
            context = self.get_context_data(**kwargs)
            context["form_errors"] = parsed["errors"]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)
        try:
            JobPostingService().update_draft(
                job_posting=job,
                recruiter=profile,
                data=parsed["data"],
            )
            return redirect(f"{self.portal_url('recruiter_jobs')}?updated=1")
        except (ValidationException, BusinessLogicException) as exc:
            context = self.get_context_data(**kwargs)
            context["form_errors"] = [str(exc)]
            context["form_data"] = parsed["form"]
            return self.render_to_response(context)


class RecruiterCandidateMarketplaceView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/candidates/marketplace/index.html"
    sidebar_active_key = "candidates"
    page_title = "Candidate Marketplace"
    page_description = (
        "Discover IT talent, filter by skills and experience, and engage candidates."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            params = {
                key: (self.request.GET.get(key) or "").strip()
                for key in self.request.GET
            }
            context["marketplace_page"] = RecruiterCandidateMarketplaceService().build(
                profile, params=params
            )
        return context


class RecruiterCandidateMarketplaceDetailView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/candidates/marketplace/detail.html"
    sidebar_active_key = "candidates"
    page_title = "Candidate Profile"
    page_description = "Review candidate details, resume, and engagement options."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if not profile:
            return context
        detail = RecruiterCandidateMarketplaceService().get_seeker_detail(
            profile, kwargs["seeker_id"]
        )
        if not detail:
            raise Http404("Candidate not found or not visible.")
        context["candidate"] = detail
        context["marketplace_url"] = self.portal_url("recruiter_candidate_marketplace")
        return context


class RecruiterSettingsView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/settings/index.html"
    sidebar_active_key = "settings"
    page_title = "Settings"
    page_description = "Account and security preferences."

    def get_context_data(self, **kwargs):
        from apps.it_recruitment.services.recruiter_settings_portal_service import (
            RecruiterSettingsPortalService,
        )

        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            portal = RecruiterSettingsPortalService()
            page = portal.build(profile, request=self.request)
            context["settings_page"] = page
            context["notification_toggles"] = portal.notification_toggles(
                page.notifications
            )
        return context


class RecruiterCandidatesView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/candidates/index.html"
    sidebar_active_key = "candidates"
    page_title = "Applicants"
    page_description = "Review applicants and manage your hiring pipeline."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            try:
                page = max(1, int(self.request.GET.get("page") or 1))
            except ValueError:
                page = 1
            context["candidates_page"] = RecruiterCandidatesPortalService().build(
                profile,
                q=(self.request.GET.get("q") or "").strip(),
                status=(self.request.GET.get("status") or "").strip(),
                job_id=(self.request.GET.get("job_id") or "").strip(),
                location=(self.request.GET.get("location") or "").strip(),
                experience_min=(self.request.GET.get("experience_min") or "").strip(),
                skills=(self.request.GET.get("skills") or "").strip(),
                education=(self.request.GET.get("education") or "").strip(),
                date_from=(self.request.GET.get("date_from") or "").strip(),
                date_to=(self.request.GET.get("date_to") or "").strip(),
                sort=(self.request.GET.get("sort") or "recent").strip(),
                page=page,
            )
        return context


class RecruiterNotificationsView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/notifications/index.html"
    sidebar_active_key = "notifications"
    page_title = "Notifications"
    page_description = "Your latest alerts and updates."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["notifications_page"] = RecruiterNotificationsPortalService().build(
                profile
            )
        return context


class RecruiterMessagesView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/messages/index.html"
    sidebar_active_key = "messages"
    page_title = "Messages"
    page_description = (
        "Application activity, candidate updates, and recruiter communications."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["messages_page"] = RecruiterMessagesPortalService().build(profile)
        return context


class RecruiterSavedCandidatesView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/saved_candidates/index.html"
    sidebar_active_key = "saved"
    page_title = "Saved Candidates"
    page_description = "Shortlisted and active pipeline candidates you are tracking."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            context["saved_page"] = RecruiterSavedCandidatesPortalService().build(
                profile,
                q=(self.request.GET.get("q") or "").strip(),
            )
        return context


class RecruiterNotificationReadView(RecruiterPortalMixin, View):
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
        return redirect(self.portal_url("recruiter_notifications"))


class RecruiterNotificationsMarkAllReadView(RecruiterPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        Notification.objects.filter(
            recipient_domain="it", recipient_id=request.user.pk, is_read=False
        ).update(is_read=True)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect(self.portal_url("recruiter_notifications"))


class RecruiterShortlistedCandidatesView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/shortlisted/index.html"
    sidebar_active_key = "shortlisted"
    page_title = "Shortlisted Candidates"
    page_description = "Manage shortlisted candidates and schedule interviews."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            user = self.request.user
            pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
            
            q = (self.request.GET.get("q") or "").strip()
            from django.core.paginator import Paginator
            from django.db.models import Q
            
            from apps.applications.models import JobApplication
            from apps.applications.selectors.application_selector import JobApplicationSelector
            qs = (
                JobApplicationSelector()
                .for_recruiter(profile)
                .filter(status="shortlisted")
                .select_related(
                    "job_posting",
                    "job_seeker",
                    "job_seeker__user",
                    "job_seeker__profile_photo",
                    "job_seeker__resume_file",
                    "company",
                )
            )
            if q:
                qs = qs.filter(
                    Q(applicant_name_snapshot__icontains=q)
                    | Q(job_title_snapshot__icontains=q)
                )

            paginator = Paginator(qs.order_by("-applied_at"), 20)
            page = max(1, int(self.request.GET.get("page") or 1))
            page_obj = paginator.get_page(page)

            service = RecruiterCandidatesPortalService()
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
                "schedule_template": pu("recruiter_interview_schedule_api", application_id=placeholder),
                "complete_template": pu("recruiter_interview_complete_api", application_id=placeholder),
                "status_template": pu("recruiter_application_status_api", application_id=placeholder),
                "notes_template": pu("recruiter_application_notes_api", application_id=placeholder),
            }
        return context


class RecruiterSelectedCandidatesView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/selected/index.html"
    sidebar_active_key = "selected"
    page_title = "Selected Candidates"
    page_description = "Track selection progression, offer acceptances, joining, and invoices."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            user = self.request.user
            pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
            
            q = (self.request.GET.get("q") or "").strip()
            from django.core.paginator import Paginator
            from django.db.models import Q
            
            from apps.applications.models import JobApplication, PlacementDetails
            from apps.applications.selectors.application_selector import JobApplicationSelector
            from apps.invoices.models import Invoice
            
            qs = (
                JobApplicationSelector()
                .for_recruiter(profile)
                .filter(status__in=["selected", "joining_in_progress"])
                .select_related(
                    "job_posting",
                    "job_seeker",
                    "job_seeker__user",
                    "job_seeker__profile_photo",
                    "job_seeker__resume_file",
                    "company",
                )
            )
            if q:
                qs = qs.filter(
                    Q(applicant_name_snapshot__icontains=q)
                    | Q(job_title_snapshot__icontains=q)
                )

            paginator = Paginator(qs.order_by("-status_changed_at"), 20)
            page = max(1, int(self.request.GET.get("page") or 1))
            page_obj = paginator.get_page(page)

            service = RecruiterCandidatesPortalService()
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
                workflow_service.update_joining_details("it", application_id, request.user, data)
                messages.success(request, "Joining details updated successfully.")
            elif action == "confirm_joined":
                data = {
                    "actual_joining_date": request.POST.get("actual_joining_date") or None,
                    "employee_id": request.POST.get("employee_id", ""),
                    "notes": request.POST.get("notes", ""),
                }
                workflow_service.confirm_joined("it", application_id, request.user, data)
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


class RecruiterJoinedCandidatesView(RecruiterPortalMixin, TemplateView):
    template_name = "it/recruiter/joined/index.html"
    sidebar_active_key = "joined"
    page_title = "Joined Candidates"
    page_description = "Monitor placement guarantee status and process refund/replacement claims."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        if profile:
            user = self.request.user
            pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
            
            q = (self.request.GET.get("q") or "").strip()
            from django.core.paginator import Paginator
            from django.db.models import Q
            from django.utils import timezone
            
            from apps.applications.models import JobApplication, PlacementDetails
            from apps.applications.selectors.application_selector import JobApplicationSelector
            from apps.invoices.models import Invoice
            from apps.guarantee_claims.models import PlacementGuarantee, PlacementClaim
            
            qs = (
                JobApplicationSelector()
                .for_recruiter(profile)
                .filter(status="joined")
                .select_related(
                    "job_posting",
                    "job_seeker",
                    "job_seeker__user",
                    "job_seeker__profile_photo",
                    "job_seeker__resume_file",
                    "company",
                )
            )
            if q:
                qs = qs.filter(
                    Q(applicant_name_snapshot__icontains=q)
                    | Q(job_title_snapshot__icontains=q)
                )

            paginator = Paginator(qs.order_by("-status_changed_at"), 20)
            page = max(1, int(self.request.GET.get("page") or 1))
            page_obj = paginator.get_page(page)

            service = RecruiterCandidatesPortalService()
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
                            job_application_id=app.pk,
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
        from apps.applications.models import JobApplication
        
        application_id = request.POST.get("application_id")
        claim_reason = request.POST.get("claim_reason")
        incident_date = request.POST.get("incident_date")
        claim_description = request.POST.get("claim_description")
        claim_type = request.POST.get("claim_type", "refund")
        
        if not application_id or not claim_reason or not incident_date or not claim_description:
            return JsonResponse({"success": False, "error": "All fields are required."}, status=400)
            
        try:
            application = JobApplication.objects.get(pk=application_id)
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

