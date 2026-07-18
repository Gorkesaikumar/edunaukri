"""Public job marketplace web views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from apps.core.exceptions.domain_exceptions import ResumeRequiredException
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.services.application_service import JobApplicationService
from apps.it_recruitment.models import JobSeekerProfile
from apps.jobs.models import JobPosting
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.jobs.services.job_marketplace_service import JobMarketplaceService
from apps.jobs.services.saved_job_service import SavedJobService


def _safe_next_url(request, fallback: str) -> str:
    nxt = (request.GET.get("next") or request.POST.get("next") or "").strip()
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return fallback


def _jobseeker_pu(request):
    user = WebJWTService.get_valid_it_user(request) or request.user
    return lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)


def _get_seeker_profile(user) -> JobSeekerProfile | None:
    if not user.is_authenticated:
        return None
    return (
        JobSeekerProfile.objects.filter(user=user, is_deleted=False)
        .select_related("resume_file")
        .first()
    )


def _is_job_seeker(user) -> bool:
    if not user.is_authenticated:
        return False
    try:
        return bool(RoleAssignmentService().user_has_it_role(user, ITUserRoleType.JOB_SEEKER))
    except AttributeError:
        return False


class MarketplaceBrowseView(TemplateView):
    """Browse jobs marketplace — guests and authenticated users."""

    template_name = "jobs/browse.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = JobMarketplaceService()
        filters = service.parse_filters(self.request.GET)
        profile = (
            _get_seeker_profile(self.request.user)
            if _is_job_seeker(self.request.user)
            else None
        )
        result = service.browse(
            filters=filters, user=self.request.user, profile=profile
        )

        context["marketplace"] = result
        context["filters"] = filters
        context["is_job_seeker"] = _is_job_seeker(self.request.user)
        context["is_authenticated"] = self.request.user.is_authenticated
        context["login_url"] = reverse("it_login_job_seeker")
        context["signup_url"] = reverse("it_signup_job_seeker")
        context["search_api_url"] = reverse("marketplace_search_api")
        context["suggest_api_url"] = reverse("marketplace_suggest_api")
        if _is_job_seeker(self.request.user):
            pu = _jobseeker_pu(self.request)
            context["saved_job_toggle_url"] = pu("jobseeker_saved_job_toggle_api")
            context["saved_job_status_url"] = pu("jobseeker_saved_job_status_api")
        return context


class MarketplaceJobDetailView(TemplateView):
    """Job detail page for the marketplace."""

    template_name = "jobs/detail.html"

    def get(self, request, job_id, *args, **kwargs):
        service = JobMarketplaceService()
        profile = (
            _get_seeker_profile(request.user) if _is_job_seeker(request.user) else None
        )
        payload = service.get_job_detail(
            job_id, user=request.user, profile=profile, domain="it"
        )
        if not payload:
            return render(request, "jobs/not_found.html", status=404)
        JobPostingRepository().increment_view_count(payload["job"])
        context = self.get_context_data(**kwargs)
        context.update(payload)
        context["search_api_url"] = reverse("marketplace_search_api")
        if _is_job_seeker(request.user):
            pu = _jobseeker_pu(request)
            context["saved_job_toggle_url"] = pu("jobseeker_saved_job_toggle_api")
            context["saved_job_status_url"] = pu("jobseeker_saved_job_status_api")
        return render(request, self.template_name, context)


class MarketplaceVacancyDetailView(TemplateView):
    """Faculty Vacancy detail page for the marketplace."""

    template_name = "jobs/vacancy_detail.html"

    def get(self, request, job_id, *args, **kwargs):
        service = JobMarketplaceService()
        payload = service.get_job_detail(
            job_id, user=request.user, profile=None, domain="faculty"
        )
        if not payload:
            return render(request, "jobs/not_found.html", status=404)

        # Increment view count
        from apps.faculty.repositories.vacancy_repository import (
            FacultyVacancyRepository,
        )

        FacultyVacancyRepository().increment_view_count(payload["job"])

        context = self.get_context_data(**kwargs)
        context.update(payload)
        context["search_api_url"] = reverse("marketplace_search_api")
        return render(request, self.template_name, context)


class MarketplaceSearchAPIView(View):
    """JSON search endpoint for AJAX / infinite scroll."""

    def get(self, request):
        service = JobMarketplaceService()
        filters = service.parse_filters(request.GET)
        profile = (
            _get_seeker_profile(request.user) if _is_job_seeker(request.user) else None
        )
        result = service.browse(filters=filters, user=request.user, profile=profile)
        return JsonResponse({"success": True, "data": result.to_dict()})


class MarketplaceSuggestAPIView(View):
    """Autocomplete suggestions."""

    def get(self, request):
        query = request.GET.get("q", "")
        items = JobMarketplaceService().suggest(query, limit=8)
        return JsonResponse({"success": True, "data": items})


@method_decorator(csrf_protect, name="dispatch")
class MarketplaceApplyJobView(LoginRequiredMixin, View):
    """Apply to a job from the marketplace."""

    login_url = "/it/login/job-seeker/"
    http_method_names = ["get", "post"]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            detail = reverse(
                "marketplace_job_detail", kwargs={"job_id": kwargs["job_id"]}
            )
            return redirect(f"{reverse('it_login_job_seeker')}?next={detail}")
        if not _is_job_seeker(request.user):
            messages.error(request, "Only job seeker accounts can apply to jobs.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, job_id):
        return redirect("marketplace_job_detail", job_id=job_id)

    def post(self, request, job_id):
        profile = _get_seeker_profile(request.user)
        pu = _jobseeker_pu(request)
        detail_url = reverse("marketplace_job_detail", kwargs={"job_id": job_id})
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
            return redirect(pu("jobseeker_profile"))

        try:
            job = get_object_or_404(
                JobPosting.objects.select_related("company"),
                pk=job_id,
                is_deleted=False,
            )
            JobApplicationService().apply(
                job_posting=job,
                job_seeker=profile,
                source="marketplace",
            )
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Application submitted successfully.",
                        "redirect_url": pu("jobseeker_applications"),
                    }
                )
            messages.success(request, "Application submitted successfully.")
            return redirect(pu("jobseeker_applications"))
        except ResumeRequiredException as exc:
            if is_ajax:
                return JsonResponse(
                    {"success": False, "code": "RESUME_REQUIRED", "message": str(exc)},
                    status=400,
                )
            messages.error(request, str(exc))
            return redirect(f"{pu('jobseeker_resume')}?next={detail_url}")
        except Exception as exc:
            if is_ajax:
                return JsonResponse({"success": False, "error": str(exc)}, status=400)
            messages.error(request, str(exc))
            return redirect(detail_url)


@method_decorator(csrf_protect, name="dispatch")
class MarketplaceSaveJobView(LoginRequiredMixin, View):
    """Save or unsave a job from the marketplace."""

    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            detail = reverse(
                "marketplace_job_detail", kwargs={"job_id": kwargs["job_id"]}
            )
            return redirect(f"{reverse('it_login_job_seeker')}?next={detail}")
        if not _is_job_seeker(request.user):
            return JsonResponse({"success": False, "error": "Forbidden."}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, job_id):
        profile = _get_seeker_profile(request.user)
        if profile is None:
            return JsonResponse(
                {"success": False, "error": "Profile required."}, status=400
            )

        try:
            result = SavedJobService().toggle(profile, job_id)
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=404)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "data": result.to_dict(),
                    "is_saved": result.is_saved,
                }
            )
        next_url = _safe_next_url(request, reverse("marketplace_browse_jobs"))
        return redirect(next_url)
