"""Public Institutions Marketplace web views."""

from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.reports.services.institution_marketplace_service import (
    InstitutionMarketplaceService,
)


def _is_job_seeker(user) -> bool:
    return bool(
        user.is_authenticated
        and RoleAssignmentService().user_has_it_role(user, ITUserRoleType.JOB_SEEKER)
    )


class InstitutionsBrowseView(TemplateView):
    template_name = "institutions/browse.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = InstitutionMarketplaceService()
        filters = service.parse_filters(self.request.GET)
        result = service.browse(filters=filters)
        context["marketplace"] = result
        context["filters"] = filters
        context["is_job_seeker"] = _is_job_seeker(self.request.user)
        context["is_authenticated"] = self.request.user.is_authenticated
        context["login_url"] = reverse("it_login_job_seeker")
        context["search_api_url"] = reverse("institutions_search_api")
        context["suggest_api_url"] = reverse("institutions_suggest_api")
        return context


class InstitutionDetailView(TemplateView):
    template_name = "institutions/detail.html"

    def get(self, request, slug, *args, **kwargs):
        service = InstitutionMarketplaceService()
        profile = service.get_profile(slug, user=request.user)
        if not profile:
            return render(request, "institutions/not_found.html", status=404)
        context = {
            "profile": profile,
            "is_job_seeker": _is_job_seeker(request.user),
            "is_authenticated": request.user.is_authenticated,
            "login_url": reverse("it_login_job_seeker"),
        }
        return render(request, self.template_name, context)


class InstitutionsSearchAPIView(View):
    def get(self, request):
        service = InstitutionMarketplaceService()
        filters = service.parse_filters(request.GET)
        result = service.browse(filters=filters)
        return JsonResponse({"success": True, "data": result.to_dict()})


class InstitutionsSuggestAPIView(View):
    def get(self, request):
        items = InstitutionMarketplaceService().suggest(request.GET.get("q", ""))
        return JsonResponse({"success": True, "data": items})
