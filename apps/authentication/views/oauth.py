"""OAuth web views — Google and LinkedIn sign-in for IT and Faculty domains."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.constants.oauth_config import provider_configured
from apps.authentication.models import OAuthProvider
from apps.authentication.services.oauth_service import OAuthService
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService

logger = logging.getLogger(__name__)


class _OAuthStartView(View):
    provider: str = ""

    def get(self, request):
        intent = request.GET.get("intent", "login")
        return_url = (request.GET.get("return") or "").strip()
        role = request.GET.get("role", "seeker")

        if intent == "connect":
            user = WebJWTService.get_valid_web_user(request)
            if user is None:
                fallback = (
                    return_url
                    if return_url.startswith("/")
                    else reverse("jobseeker_portal_entry")
                )
                return redirect(
                    f"{reverse('it_login_job_seeker')}?next={_quote(fallback)}"
                )
            settings_url = PortalURLService.settings_for_user(user)
            fallback = return_url if return_url.startswith("/") else settings_url
            roles = RoleAssignmentService()
            if isinstance(user, ProfessorUser):
                role = "professor"
            elif isinstance(user, CollegeUser):
                role = "college"
            else:
                role = (
                    "recruiter"
                    if roles.user_has_it_role(user, ITUserRoleType.RECRUITER)
                    else "seeker"
                )
            if not provider_configured(self.provider):
                return redirect(
                    f"{fallback}?oauth_error={_quote('OAuth is not configured.')}"
                )
            try:
                result = OAuthService().start_authorization(
                    provider=self.provider,
                    role=role,
                    request=request,
                    intent="connect",
                    return_url=fallback,
                )
                return redirect(result.authorize_url)
            except ValidationError as exc:
                messages = exc.messages if hasattr(exc, "messages") else [str(exc)]
                return redirect(f"{fallback}?oauth_error={_quote(messages[0])}")

        if role == "institution":
            role = "college"

        if role == "professor":
            login_name = "faculty_login_professor"
        elif role == "college":
            login_name = "faculty_login_institution"
        else:
            login_name = (
                "it_login_recruiter" if role == "recruiter" else "it_login_job_seeker"
            )
        login_url = reverse(login_name)

        if not provider_configured(self.provider):
            return redirect(
                f"{login_url}?oauth_error=OAuth+is+not+configured.+Contact+support."
            )

        try:
            result = OAuthService().start_authorization(
                provider=self.provider, role=role, request=request, intent="login"
            )
            return redirect(result.authorize_url)
        except ValidationError as exc:
            messages = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return redirect(f"{login_url}?oauth_error={_quote(messages[0])}")


class _OAuthCallbackView(View):
    provider: str = ""

    def get(self, request):
        role = request.session.get(OAuthService.SESSION_ROLE_KEY, "seeker")
        if role == "professor":
            login_name = "faculty_login_professor"
            settings_url = reverse("professor_portal_entry")
        elif role == "college":
            login_name = "faculty_login_institution"
            settings_url = reverse("college_portal_entry")
        else:
            login_name = (
                "it_login_recruiter" if role == "recruiter" else "it_login_job_seeker"
            )
            settings_url = reverse(
                "recruiter_portal_entry"
                if role == "recruiter"
                else "jobseeker_portal_entry"
            )
        login_url = reverse(login_name)

        intent_hint = request.session.get(OAuthService.SESSION_INTENT_KEY, "login")
        return_hint = request.session.get(OAuthService.SESSION_RETURN_KEY, "")

        try:
            user, intended_role, intent, return_url = (
                OAuthService().complete_authorization(
                    provider=self.provider, request=request
                )
            )

            if intent == "connect":
                target = (
                    return_url
                    if return_url.startswith("/")
                    else PortalURLService.settings_for_user(user)
                )
                provider_label = (
                    "Google" if self.provider == OAuthProvider.GOOGLE else "LinkedIn"
                )
                return redirect(
                    f"{target}?oauth_success={_quote(provider_label + ' account connected successfully.')}"
                )

            if intended_role == "professor":
                if not isinstance(user, ProfessorUser):
                    SessionService().logout(request)
                    return redirect(
                        f"{login_url}?oauth_error=This+account+is+not+registered+for+the+selected+role."
                    )
                auth_domain = "professor"
            elif intended_role == "college":
                if not isinstance(user, CollegeUser):
                    SessionService().logout(request)
                    return redirect(
                        f"{login_url}?oauth_error=This+account+is+not+registered+for+the+selected+role."
                    )
                auth_domain = "college"
            else:
                required_role = (
                    ITUserRoleType.RECRUITER
                    if intended_role == "recruiter"
                    else ITUserRoleType.JOB_SEEKER
                )
                if not RoleAssignmentService().user_has_it_role(user, required_role):
                    SessionService().logout(request)
                    return redirect(
                        f"{login_url}?oauth_error=This+account+is+not+registered+for+the+selected+role."
                    )
                auth_domain = "it"

            from apps.accounts.constants.enums import AccountStatus
            if getattr(user, "account_status", None) == AccountStatus.SUSPENDED:
                SessionService().logout(request)
                return redirect(
                    f"{login_url}?oauth_error=Your+account+has+been+suspended."
                )

            SessionService().login_user(request, domain=auth_domain, user=user)
            response = redirect(PortalURLService.dashboard_for_user(user))
            WebJWTService().attach_tokens_with_request(
                response,
                user=user,
                domain=auth_domain,
                request=request,
                auth_method=self.provider,
            )
            return response
        except ValidationError as exc:
            messages = exc.messages if hasattr(exc, "messages") else [str(exc)]
            if intent_hint == "connect":
                target = return_hint if return_hint.startswith("/") else settings_url
                return redirect(f"{target}?oauth_error={_quote(messages[0])}")
            return redirect(f"{login_url}?oauth_error={_quote(messages[0])}")
        except Exception:
            logger.exception("OAuth callback failed for provider=%s", self.provider)
            return redirect(
                f"{login_url}?oauth_error=Sign-in+failed.+Please+try+again."
            )


class GoogleOAuthStartView(_OAuthStartView):
    provider = OAuthProvider.GOOGLE


class GoogleOAuthCallbackView(_OAuthCallbackView):
    provider = OAuthProvider.GOOGLE


class LinkedInOAuthStartView(_OAuthStartView):
    provider = OAuthProvider.LINKEDIN


class LinkedInOAuthCallbackView(_OAuthCallbackView):
    provider = OAuthProvider.LINKEDIN


def _quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")
