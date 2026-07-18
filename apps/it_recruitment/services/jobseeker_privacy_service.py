"""Enterprise privacy enforcement for IT job seeker profiles."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.profiles.constants.enums import ProfileStatus, ProfileVisibility
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.models import JobApplication
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerAccountSettings, JobSeekerProfile
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector
from apps.it_recruitment.services.account_settings_service import AccountSettingsService


HIDDEN_CONTACT_LABEL = "Hidden by candidate"
CONTACT_DECLINED_MESSAGE = (
    "This candidate is currently not accepting direct recruiter contact."
)
RESUME_DOWNLOAD_DENIED = "This candidate has disabled resume downloads."

VISIBILITY_UI_LABELS = {
    ProfileVisibility.PUBLIC: "Public",
    ProfileVisibility.EMPLOYERS_ONLY: "Recruiters Only",
    ProfileVisibility.PRIVATE: "Private",
}

PRIVACY_FIELD_LABELS = {
    "profile_visibility": "Profile visibility",
    "allow_recruiter_resume_download": "Resume download permission",
    "allow_recruiter_contact": "Recruiter contact permission",
    "show_email_on_profile": "Email visibility",
    "show_phone_on_profile": "Phone visibility",
}

PRIVACY_SUCCESS_MESSAGES = {
    "profile_visibility": "Profile visibility updated.",
    "allow_recruiter_resume_download": "Resume download permission updated.",
    "allow_recruiter_contact": "Recruiter contact permission updated.",
    "show_email_on_profile": "Email visibility updated.",
    "show_phone_on_profile": "Phone visibility updated.",
}


class JobSeekerPrivacyService(BaseService):
    """Central permission checks and contact masking for job seeker privacy."""

    def __init__(self):
        self._settings_svc = AccountSettingsService()

    def get_settings(self, profile: JobSeekerProfile) -> JobSeekerAccountSettings:
        return self._settings_svc.get_or_create_settings(profile)

    @staticmethod
    def visibility_options_for_ui() -> list[tuple[str, str]]:
        return [
            (value, VISIBILITY_UI_LABELS.get(value, label))
            for value, label in ProfileVisibility.choices
        ]

    @staticmethod
    def is_admin(viewer) -> bool:
        return isinstance(viewer, AdminUser)

    @staticmethod
    def is_recruiter(viewer) -> bool:
        if not isinstance(viewer, ITUser):
            return False
        return ITUserRoleType.RECRUITER in RoleAssignmentService().get_it_roles(viewer)

    def is_owner(self, profile: JobSeekerProfile, viewer) -> bool:
        return (
            viewer is not None
            and getattr(viewer, "is_authenticated", False)
            and getattr(profile, "user_id", None) == getattr(viewer, "pk", None)
        )

    def has_recruiter_application(self, profile: JobSeekerProfile, viewer) -> bool:
        if not self.is_recruiter(viewer):
            return False
        recruiter = RecruiterProfileSelector().for_user(viewer)
        if not recruiter:
            return False
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        return JobApplication.objects.filter(
            job_seeker=profile,
            is_deleted=False,
            job_posting__company_id__in=company_ids,
        ).exists()

    def can_discover_in_search(self, profile: JobSeekerProfile, viewer) -> bool:
        if self.is_admin(viewer) or self.is_owner(profile, viewer):
            return True
        if (
            getattr(profile, "profile_status", ProfileStatus.ACTIVE)
            != ProfileStatus.ACTIVE
        ):
            return False
        visibility = getattr(profile, "profile_visibility", ProfileVisibility.PRIVATE)
        if visibility == ProfileVisibility.PRIVATE:
            return False
        if not self.is_recruiter(viewer):
            return False
        return visibility in (
            ProfileVisibility.PUBLIC,
            ProfileVisibility.EMPLOYERS_ONLY,
        )

    def filter_searchable_queryset(self, qs: QuerySet, viewer) -> QuerySet:
        if self.is_admin(viewer):
            return qs
        if not self.is_recruiter(viewer):
            return qs.none()
        return qs.filter(
            profile_status=ProfileStatus.ACTIVE,
            profile_visibility__in=(
                ProfileVisibility.PUBLIC,
                ProfileVisibility.EMPLOYERS_ONLY,
            ),
        )

    def can_view_profile(
        self,
        profile: JobSeekerProfile,
        viewer,
        *,
        application: JobApplication | None = None,
    ) -> bool:
        if self.is_admin(viewer) or self.is_owner(profile, viewer):
            return True
        if (
            getattr(profile, "profile_status", ProfileStatus.ACTIVE)
            != ProfileStatus.ACTIVE
        ):
            return False

        visibility = getattr(profile, "profile_visibility", ProfileVisibility.PRIVATE)
        if visibility == ProfileVisibility.PUBLIC:
            return True
        if visibility == ProfileVisibility.EMPLOYERS_ONLY:
            return self.is_recruiter(viewer)
        if visibility == ProfileVisibility.PRIVATE:
            if application is not None:
                return self._viewer_can_access_application(application, viewer)
            return self.has_recruiter_application(profile, viewer)
        return False

    def ensure_can_view_profile(
        self,
        profile: JobSeekerProfile,
        viewer,
        *,
        application: JobApplication | None = None,
    ) -> None:
        if not self.can_view_profile(profile, viewer, application=application):
            raise PermissionDeniedException(
                "You do not have permission to view this profile."
            )

    def can_download_resume(
        self,
        profile: JobSeekerProfile,
        viewer,
        *,
        application: JobApplication | None = None,
    ) -> bool:
        if self.is_admin(viewer) or self.is_owner(profile, viewer):
            return True
        if not self.is_recruiter(viewer):
            return False
        if application is not None and not self._viewer_can_access_application(
            application, viewer
        ):
            return False
        if not self.can_view_profile(profile, viewer, application=application):
            return False
        settings = self.get_settings(profile)
        return bool(settings.allow_recruiter_resume_download)

    def ensure_can_download_resume(
        self,
        profile: JobSeekerProfile,
        viewer,
        *,
        application: JobApplication | None = None,
    ) -> None:
        if not self.can_download_resume(profile, viewer, application=application):
            raise PermissionDenied(RESUME_DOWNLOAD_DENIED)

    def can_recruiter_contact(
        self,
        profile: JobSeekerProfile,
        viewer,
        *,
        application: JobApplication | None = None,
    ) -> bool:
        if self.is_admin(viewer) or self.is_owner(profile, viewer):
            return True
        if not self.is_recruiter(viewer):
            return False
        if application is not None and not self._viewer_can_access_application(
            application, viewer
        ):
            return False
        settings = self.get_settings(profile)
        return bool(settings.allow_recruiter_contact)

    def ensure_can_recruiter_contact(
        self,
        profile: JobSeekerProfile,
        viewer,
        *,
        application: JobApplication | None = None,
    ) -> None:
        if not self.can_recruiter_contact(profile, viewer, application=application):
            raise PermissionDenied(CONTACT_DECLINED_MESSAGE)

    def contact_fields_for_viewer(
        self, profile: JobSeekerProfile, viewer
    ) -> dict[str, str]:
        settings = self.get_settings(profile)
        email = profile.user.email if hasattr(profile, "user") and profile.user else ""
        phone = profile.phone or ""

        if self.is_admin(viewer) or self.is_owner(profile, viewer):
            return {"email": email, "phone": phone}

        if not settings.show_email_on_profile:
            email = HIDDEN_CONTACT_LABEL
        if not settings.show_phone_on_profile:
            phone = HIDDEN_CONTACT_LABEL
        return {"email": email, "phone": phone}

    def mask_profile_data(self, profile: JobSeekerProfile, viewer, data: dict) -> dict:
        if self.is_admin(viewer) or self.is_owner(profile, viewer):
            if hasattr(profile, "user") and profile.user:
                data.setdefault("email", profile.user.email)
            return data

        contact = self.contact_fields_for_viewer(profile, viewer)
        if "phone" in data:
            data["phone"] = contact["phone"]
        data["email"] = contact["email"]
        return data

    def recruiter_permissions_for_application(
        self, application: JobApplication, viewer
    ) -> dict[str, bool | str]:
        profile = application.job_seeker
        can_contact = self.can_recruiter_contact(
            profile, viewer, application=application
        )
        return {
            "can_download_resume": self.can_download_resume(
                profile, viewer, application=application
            ),
            "can_contact": can_contact,
            "contact_declined_message": "" if can_contact else CONTACT_DECLINED_MESSAGE,
            **self.contact_fields_for_viewer(profile, viewer),
        }

    @staticmethod
    def _viewer_can_access_application(application: JobApplication, viewer) -> bool:
        from apps.applications.services.application_authorization_service import (
            ApplicationAuthorizationService,
        )

        try:
            ApplicationAuthorizationService().ensure_can_view_it_application(
                application, viewer
            )
            return True
        except PermissionDeniedException:
            return False
