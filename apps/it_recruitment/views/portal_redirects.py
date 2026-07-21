"""Redirect legacy flat portal URLs to UUID-scoped routes."""

from __future__ import annotations

from urllib.parse import quote

from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService


class _LegacyPortalRedirectView(View):
    login_url_name: str = "it_login_job_seeker"
    portal_prefix: str = "jobseeker"
    default_subpath: str = "dashboard/"

    def get(self, request, legacy_path: str = ""):
        user = WebJWTService.get_valid_it_user(request)
        if user is None:
            next_url = quote(request.get_full_path(), safe="")
            return redirect(f"{reverse(self.login_url_name)}?next={next_url}")

        subpath = (legacy_path or self.default_subpath).strip("/")
        target = PortalURLService.scoped_path(self.portal_prefix, user.pk, subpath)
        return redirect(target)


class JobSeekerPortalEntryRedirectView(View):
    """Redirect /jobseeker/ to the authenticated user's UUID dashboard."""

    def get(self, request, *args, **kwargs):
        user = WebJWTService.get_valid_it_user(request)
        if user is None:
            return redirect(
                f"{reverse('it_login_job_seeker')}?next={quote('/jobseeker/', safe='')}"
            )
        return redirect(PortalURLService.jobseeker(user, "jobseeker_dashboard"))


class JobSeekerLegacyRedirectView(_LegacyPortalRedirectView):
    login_url_name = "it_login_job_seeker"
    portal_prefix = "jobseeker"
    default_subpath = "dashboard/"


class RecruiterPortalEntryRedirectView(View):
    def get(self, request, *args, **kwargs):
        user = WebJWTService.get_valid_it_user(request)
        if user is None:
            return redirect(
                f"{reverse('it_login_recruiter')}?next={quote('/recruiter/', safe='')}"
            )
        return redirect(PortalURLService.recruiter(user, "recruiter_dashboard"))


class RecruiterLegacyRedirectView(_LegacyPortalRedirectView):
    login_url_name = "it_login_recruiter"
    portal_prefix = "recruiter"
    default_subpath = "dashboard/"
