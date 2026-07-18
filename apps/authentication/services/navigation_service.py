"""Build authentication-aware navigation context for templates."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.urls import reverse

from apps.authentication.services.portal_url_service import PortalURLService

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.it_user import ITUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile


def _initials(name: str, fallback: str = "U") -> str:
    parts = (name or "").strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    if parts and parts[0]:
        token = parts[0]
        return token[:2].upper() if len(token) >= 2 else token[0].upper()
    if fallback:
        return fallback[:2].upper()
    return "U"


def _media_url(stored_file) -> str | None:
    if not stored_file or not getattr(stored_file, "storage_path", None):
        return None
    from django.conf import settings

    path = stored_file.storage_path.lstrip("/")
    return f"{settings.MEDIA_URL}{path}"


@dataclass
class NavMenuItem:
    label: str
    url: str
    icon: str = ""


@dataclass
class NavigationContext:
    is_authenticated: bool = False
    display_name: str = ""
    initials: str = ""
    avatar_url: str | None = None
    role: str = ""
    role_label: str = ""
    menu: list[NavMenuItem] = field(default_factory=list)
    dashboard_url: str = ""
    logout_url: str = ""

    def to_template_dict(self) -> dict:
        return {
            "is_authenticated": self.is_authenticated,
            "display_name": self.display_name,
            "initials": self.initials,
            "avatar_url": self.avatar_url,
            "role": self.role,
            "role_label": self.role_label,
            "menu": [
                {"label": i.label, "url": i.url, "icon": i.icon} for i in self.menu
            ],
            "dashboard_url": self.dashboard_url,
            "logout_url": self.logout_url,
        }


class NavigationService:
    """Resolve header navigation from the current request user."""

    def build(self, request) -> NavigationContext:
        user = WebJWTService.resolve_it_user(request)
        if user is None:
            return NavigationContext(
                is_authenticated=False, logout_url=reverse("logout")
            )

        roles = RoleAssignmentService()
        is_recruiter = roles.user_has_it_role(user, ITUserRoleType.RECRUITER)
        is_seeker = roles.user_has_it_role(user, ITUserRoleType.JOB_SEEKER)

        if is_recruiter:
            return self._recruiter_nav(user)
        if is_seeker:
            return self._seeker_nav(user)
        return NavigationContext(is_authenticated=False, logout_url=reverse("logout"))

    def _seeker_nav(self, user: ITUser) -> NavigationContext:
        profile = (
            JobSeekerProfile.objects.filter(user=user, is_deleted=False)
            .select_related("profile_photo")
            .first()
        )
        display_name = profile.full_name if profile else user.email.split("@")[0]
        avatar = (
            _media_url(profile.profile_photo)
            if profile and profile.profile_photo
            else None
        )

        pu = lambda name: PortalURLService.jobseeker(user, name)
        menu = [
            NavMenuItem("My Dashboard", pu("jobseeker_dashboard"), "bi-speedometer2"),
            NavMenuItem("My Profile", pu("jobseeker_profile"), "bi-person"),
            NavMenuItem("Applications", pu("jobseeker_applications"), "bi-briefcase"),
            NavMenuItem("Saved Jobs", pu("jobseeker_saved_jobs"), "bi-bookmark"),
            NavMenuItem("Settings", pu("jobseeker_settings"), "bi-gear"),
            NavMenuItem("Notifications", pu("jobseeker_notifications"), "bi-bell"),
        ]
        return NavigationContext(
            is_authenticated=True,
            display_name=display_name,
            initials=_initials(display_name, user.email[:2]),
            avatar_url=avatar,
            role="job_seeker",
            role_label="Job Seeker",
            menu=menu,
            dashboard_url=pu("jobseeker_dashboard"),
            logout_url=reverse("logout"),
        )

    def _recruiter_nav(self, user: ITUser) -> NavigationContext:
        profile = (
            RecruiterProfile.objects.filter(user=user, is_deleted=False)
            .select_related("profile_image")
            .first()
        )
        display_name = profile.full_name if profile else user.email.split("@")[0]
        avatar = (
            _media_url(profile.profile_image)
            if profile and profile.profile_image
            else None
        )

        pr = lambda name: PortalURLService.recruiter(user, name)
        menu = [
            NavMenuItem("My Dashboard", pr("recruiter_dashboard"), "bi-speedometer2"),
            NavMenuItem("Company Profile", pr("recruiter_profile"), "bi-building"),
            NavMenuItem("Posted Jobs", pr("recruiter_jobs"), "bi-briefcase"),
            NavMenuItem("Candidates", pr("recruiter_candidates"), "bi-people"),
            NavMenuItem("Settings", pr("recruiter_settings"), "bi-gear"),
            NavMenuItem("Notifications", pr("recruiter_notifications"), "bi-bell"),
        ]
        return NavigationContext(
            is_authenticated=True,
            display_name=display_name,
            initials=_initials(display_name, user.email[:2]),
            avatar_url=avatar,
            role="recruiter",
            role_label="Recruiter",
            menu=menu,
            dashboard_url=pr("recruiter_dashboard"),
            logout_url=reverse("logout"),
        )
