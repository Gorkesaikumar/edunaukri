"""Redirect legacy flat faculty portal URLs to UUID-scoped routes."""

from __future__ import annotations

from urllib.parse import quote

from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService


class ProfessorPortalEntryRedirectView(View):
    def get(self, request):
        user = WebJWTService.get_valid_web_user(request)
        if user is None or not isinstance(user, ProfessorUser):
            return redirect(
                f"{reverse('faculty_login_professor')}?next={quote('/professor/', safe='')}"
            )
        return redirect(PortalURLService.professor(user, "professor_dashboard"))


class CollegePortalEntryRedirectView(View):
    def get(self, request):
        user = WebJWTService.get_valid_web_user(request)
        if user is None or not isinstance(user, CollegeUser):
            return redirect(
                f"{reverse('faculty_login_institution')}?next={quote('/college/', safe='')}"
            )
        return redirect(PortalURLService.college(user, "college_dashboard"))
