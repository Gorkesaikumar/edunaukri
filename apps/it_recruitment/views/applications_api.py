"""Job seeker application portal JSON API."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.selectors.application_selector import JobApplicationSelector
from apps.applications.services.application_service import JobApplicationService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_application_portal_service import (
    JobSeekerApplicationPortalService,
)


def _get_profile(user) -> JobSeekerProfile | None:
    return JobSeekerProfile.objects.filter(user=user, is_deleted=False).first()


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


class JobSeekerApplicationsAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"

    def get(self, request, *args, **kwargs):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return _forbidden()
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        page = max(1, int(request.GET.get("page") or 1))
        result = JobSeekerApplicationPortalService().list_applications(
            profile,
            page=page,
            status=(request.GET.get("status") or "").strip(),
            q=(request.GET.get("q") or "").strip(),
            active_only=request.GET.get("active") == "1",
            interview_only=request.GET.get("interview") == "1",
            offer_only=request.GET.get("offer") == "1",
            rejected_only=request.GET.get("rejected") == "1",
        )
        return JsonResponse({"success": True, "data": _serialize_list(result)})


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerApplicationWithdrawAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return _forbidden()
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        app = (
            JobApplicationSelector()
            .for_seeker(profile)
            .filter(pk=application_id)
            .first()
        )
        if not app:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        if not JobSeekerApplicationPortalService.can_withdraw(app):
            return JsonResponse(
                {
                    "success": False,
                    "error": "This application cannot be withdrawn at the current stage.",
                },
                status=400,
            )
        try:
            JobApplicationService().withdraw(app, actor=request.user)
            return JsonResponse(
                {"success": True, "message": "Application withdrawn successfully."}
            )
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class JobSeekerApplicationOfferAPIView(LoginRequiredMixin, View):
    login_url = "/it/login/job-seeker/"
    http_method_names = ["post"]

    def post(self, request, application_id):
        if not RoleAssignmentService().user_has_it_role(
            request.user, ITUserRoleType.JOB_SEEKER
        ):
            return _forbidden()
        profile = _get_profile(request.user)
        if not profile:
            return JsonResponse(
                {"success": False, "error": "Profile not found."}, status=404
            )

        action = (request.POST.get("action") or "").strip().lower()
        app = (
            JobApplicationSelector()
            .for_seeker(profile)
            .filter(pk=application_id)
            .first()
        )
        if not app:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        if not JobSeekerApplicationPortalService.can_respond_to_offer(app):
            return JsonResponse(
                {"success": False, "error": "No pending offer to respond to."},
                status=400,
            )

        new_status = (
            JobApplicationStatus.OFFER_ACCEPTED
            if action == "accept"
            else JobApplicationStatus.OFFER_DECLINED
        )
        if action not in {"accept", "decline"}:
            return JsonResponse(
                {"success": False, "error": "Invalid action."}, status=400
            )

        try:
            JobApplicationService().update_status_for_actor(
                app,
                new_status,
                "Offer accepted by candidate."
                if action == "accept"
                else "Offer declined by candidate.",
                actor=request.user,
            )
            message = (
                "Offer accepted successfully."
                if action == "accept"
                else "Offer declined."
            )
            return JsonResponse({"success": True, "message": message})
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _serialize_list(result) -> dict:
    return {
        "applications": [
            {
                "id": card.id,
                "title": card.title,
                "company_name": card.company_name,
                "company_verified": card.company_verified,
                "logo_url": card.logo_url,
                "logo_initial": card.logo_initial,
                "domain_label": card.domain_label,
                "status": card.status,
                "status_label": card.status_label,
                "status_badge": card.status_badge,
                "status_icon": card.status_icon,
                "applied_date": card.applied_date,
                "last_updated": card.last_updated,
                "match_percent": card.match_percent,
                "recruiter_name": card.recruiter_name,
                "recruiter_avatar": card.recruiter_avatar,
                "detail_url": card.detail_url,
                "is_active": card.is_active,
            }
            for card in result.applications
        ],
        "analytics": [
            {
                "key": item.key,
                "label": item.label,
                "value": item.value,
                "icon": item.icon,
                "tone": item.tone,
            }
            for item in result.analytics
        ],
        "total_count": result.total_count,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
        "filters": result.filters,
    }
