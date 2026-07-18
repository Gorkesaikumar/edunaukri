"""Redirect legacy flat Super Admin portal URLs to UUID-scoped routes."""

from __future__ import annotations

from urllib.parse import quote

from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from apps.accounts.models.admin_user import AdminUser
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService


class SuperAdminPortalEntryRedirectView(View):
    """Redirect /super-admin/ to the authenticated admin's UUID dashboard."""

    def get(self, request):
        user = WebJWTService.resolve_web_user(request)
        if user is None or not isinstance(user, AdminUser):
            return redirect(
                f"{reverse('super_admin_login')}?next={quote('/super-admin/', safe='')}"
            )
        return redirect(PortalURLService.super_admin(user, "super_admin_dashboard"))


class SuperAdminLegacyRedirectView(View):
    """Redirect /super-admin/<legacy_path>/ to the authenticated admin's UUID dashboard."""

    default_subpath: str = "dashboard/"

    def get(self, request, legacy_path: str = ""):
        user = WebJWTService.resolve_web_user(request)
        if user is None or not isinstance(user, AdminUser):
            next_url = quote(request.get_full_path(), safe="")
            return redirect(f"{reverse('super_admin_login')}?next={next_url}")

        subpath = (legacy_path or self.default_subpath).strip("/")
        target = PortalURLService.scoped_path("super-admin", user.pk, subpath)
        return redirect(target)
