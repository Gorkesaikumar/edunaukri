"""Professor account settings — account info, notifications, privacy, deletion."""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.profiles.constants.enums import ProfileStatus
from apps.authentication.models import LoginAttempt
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.models.account_settings import ProfessorAccountSettings
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService

PROFESSOR_DOMAIN = "professor"

NOTIFICATION_FIELDS = (
    "notify_vacancy_recommendations",
    "notify_institution_messages",
    "notify_application_updates",
    "notify_interviews",
    "notify_offers",
    "notify_marketing",
    "notify_security_alerts",
    "notify_profile_views",
    "notify_cv_downloads",
    "notify_weekly_digest",
)

PRIVACY_FIELDS = (
    "allow_institution_cv_download",
    "allow_institution_contact",
    "show_email_on_profile",
    "show_phone_on_profile",
)


class ProfessorAccountSettingsService(BaseService):
    def __init__(self):
        self.audit = SecurityAuditService()
        self.sessions = SessionManagementService()

    def get_or_create_settings(
        self, profile: ProfessorProfile
    ) -> ProfessorAccountSettings:
        settings, created = ProfessorAccountSettings.objects.get_or_create(
            professor=profile,
            defaults=ProfessorAccountSettings.defaults(),
        )
        if created:
            settings.created_by_id = profile.user_id
            settings.save(update_fields=["created_by_id"])
        return settings

    @BaseService.atomic
    def update_account_info(
        self, profile: ProfessorProfile, data: dict, *, request_meta: dict
    ) -> dict:
        if "first_name" in data:
            first = (data.get("first_name") or "").strip()
            if not first:
                raise ValidationException("First name is required.")
            profile.first_name = first
        if "last_name" in data:
            profile.last_name = (data.get("last_name") or "").strip()
        if "phone" in data:
            profile.phone = (data.get("phone") or "").strip()
        profile.save(update_fields=["first_name", "last_name", "phone", "updated_at"])
        if "phone" in data:
            settings = self.get_or_create_settings(profile)
            settings.phone_verified = False
            settings.save(update_fields=["phone_verified", "updated_at"])
            self.audit.record(
                domain=PROFESSOR_DOMAIN,
                user_id=profile.user_id,
                event_type="phone.updated",
                title="Phone number updated",
                description="Your mobile number was updated.",
                ip_address=request_meta.get("ip_address"),
            )
        return self.build_account_info(profile)

    @BaseService.atomic
    def update_notifications(self, profile: ProfessorProfile, data: dict) -> dict:
        settings = self.get_or_create_settings(profile)
        for field in NOTIFICATION_FIELDS:
            if field in data:
                setattr(settings, field, bool(data[field]))
        settings.save()
        return self.build_notification_prefs(settings)

    @BaseService.atomic
    def delete_account(
        self, profile: ProfessorProfile, *, password: str, actor_id, request_meta: dict
    ) -> None:
        user = profile.user
        if not user.check_password(password):
            raise ValidationException("Password confirmation is incorrect.")
        self.sessions.revoke_other_sessions(domain=PROFESSOR_DOMAIN, user_id=user.pk)
        profile.profile_status = ProfileStatus.DEACTIVATED
        profile.is_deleted = True
        profile.deleted_at = timezone.now()
        profile.deleted_by_id = actor_id
        profile.save(
            update_fields=[
                "profile_status",
                "is_deleted",
                "deleted_at",
                "deleted_by_id",
                "updated_at",
            ]
        )
        user.is_active = False
        user.account_status = AccountStatus.DEACTIVATED
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.save(
            update_fields=[
                "is_active",
                "account_status",
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )
        self.audit.record(
            domain=PROFESSOR_DOMAIN,
            user_id=user.pk,
            event_type="account.deleted",
            title="Account deletion requested",
            description="Your faculty job seeker account was deactivated and scheduled for removal.",
            ip_address=request_meta.get("ip_address"),
        )

    def build_account_info(self, profile: ProfessorProfile) -> dict:
        user = profile.user
        settings = self.get_or_create_settings(profile)
        attempt = (
            LoginAttempt.objects.filter(
                domain=PROFESSOR_DOMAIN, user_id=user.pk, result="success"
            )
            .order_by("-attempted_at")
            .first()
        )
        return {
            "full_name": profile.full_name,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": user.email,
            "phone": profile.phone or "",
            "username": user.email.split("@")[0] if user.email else "",
            "registered_label": timezone.localtime(user.created_at).strftime(
                "%b %d, %Y"
            )
            if user.created_at
            else "—",
            "last_login_label": timezone.localtime(attempt.attempted_at).strftime(
                "%b %d, %Y · %I:%M %p"
            )
            if attempt
            else "—",
            "account_status_label": user.get_account_status_display()
            if hasattr(user, "get_account_status_display")
            else str(user.account_status).replace("_", " ").title(),
            "email_verified": bool(getattr(user, "email_verified", False)),
            "phone_verified": settings.phone_verified,
        }

    @staticmethod
    def build_notification_prefs(settings: ProfessorAccountSettings) -> dict:
        return {field: getattr(settings, field) for field in NOTIFICATION_FIELDS}

    @staticmethod
    def build_privacy_settings(
        profile: ProfessorProfile, settings: ProfessorAccountSettings
    ) -> dict:
        from apps.academic_recruitment.services.professor_privacy_settings_service import (
            ProfessorPrivacySettingsService,
        )

        return {
            "profile_visibility": profile.profile_visibility,
            "visibility_options": ProfessorPrivacySettingsService.visibility_options_for_ui(),
            **{field: getattr(settings, field) for field in PRIVACY_FIELDS},
        }

    def build_security_summary(self, profile: ProfessorProfile) -> dict:
        user = profile.user
        settings = self.get_or_create_settings(profile)
        attempt = (
            LoginAttempt.objects.filter(
                domain=PROFESSOR_DOMAIN, user_id=user.pk, result="success"
            )
            .order_by("-attempted_at")
            .first()
        )
        recommendations = []
        if not getattr(user, "email_verified", False):
            recommendations.append("Verify your email address.")
        if profile.phone and not settings.phone_verified:
            recommendations.append("Verify your mobile number.")
        if not settings.password_changed_at:
            recommendations.append("Update your password regularly.")
        if getattr(profile, "profile_completeness", 100) < 80:
            recommendations.append("Complete your profile to improve visibility.")
        return {
            "password_changed_label": timezone.localtime(
                settings.password_changed_at
            ).strftime("%b %d, %Y")
            if settings.password_changed_at
            else "Never changed",
            "last_login_label": timezone.localtime(attempt.attempted_at).strftime(
                "%b %d, %Y · %I:%M %p"
            )
            if attempt
            else "—",
            "failed_login_attempts": user.failed_login_attempts,
            "security_status": "Good"
            if getattr(user, "email_verified", False) and settings.password_changed_at
            else "Needs attention",
            "recommendations": recommendations,
        }
