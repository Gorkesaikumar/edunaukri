"""Institution recruiter account settings — account info, notifications, privacy, deletion."""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.college_user import CollegeUser
from apps.authentication.models import LoginAttempt
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.academic_recruitment.models.account_settings import CollegeAccountSettings
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService

COLLEGE_DOMAIN = "college"

NOTIFICATION_FIELDS = (
    "notify_new_applications",
    "notify_application_updates",
    "notify_interviews",
    "notify_offers",
    "notify_vacancy_updates",
    "notify_verification_alerts",
    "notify_faculty_messages",
    "notify_marketing",
    "notify_security_alerts",
    "notify_weekly_digest",
)

PRIVACY_FIELDS = (
    "show_email_to_applicants",
    "show_phone_to_applicants",
    "allow_direct_applicant_contact",
)


class CollegeAccountSettingsService(BaseService):
    def __init__(self):
        self.audit = SecurityAuditService()
        self.sessions = SessionManagementService()

    def get_or_create_settings(self, user: CollegeUser) -> CollegeAccountSettings:
        settings, created = CollegeAccountSettings.objects.get_or_create(
            college_user=user,
            defaults=CollegeAccountSettings.defaults(),
        )
        if created:
            settings.created_by_id = user.pk
            settings.save(update_fields=["created_by_id"])
        return settings

    @BaseService.atomic
    def update_account_info(
        self, user: CollegeUser, data: dict, *, request_meta: dict
    ) -> dict:
        settings = self.get_or_create_settings(user)
        first = (data.get("first_name") or "").strip()
        last = (data.get("last_name") or "").strip()
        phone = (data.get("phone") or "").strip()
        if first:
            settings.first_name = first
        if last:
            settings.last_name = last
        if "phone" in data:
            settings.phone = phone
            settings.phone_verified = False
        settings.save(
            update_fields=[
                "first_name",
                "last_name",
                "phone",
                "phone_verified",
                "updated_at",
            ]
        )
        if "phone" in data:
            self.audit.record(
                domain=COLLEGE_DOMAIN,
                user_id=user.pk,
                event_type="phone.updated",
                title="Phone number updated",
                description="Your mobile number was updated.",
                ip_address=request_meta.get("ip_address"),
            )
        return self.build_account_info(user)

    @BaseService.atomic
    def update_notifications(self, user: CollegeUser, data: dict) -> dict:
        settings = self.get_or_create_settings(user)
        for field in NOTIFICATION_FIELDS:
            if field in data:
                setattr(settings, field, bool(data[field]))
        settings.save()
        return self.build_notification_prefs(settings)

    @BaseService.atomic
    def update_privacy(self, user: CollegeUser, data: dict) -> dict:
        settings = self.get_or_create_settings(user)
        changed = []
        for field in PRIVACY_FIELDS:
            if field in data:
                setattr(settings, field, bool(data[field]))
                changed.append(field)
        if changed:
            settings.save()
        return {
            "data": self.build_privacy_settings(settings),
            "message": "Contact preferences saved.",
            "changed_fields": changed,
        }

    @BaseService.atomic
    def delete_account(
        self, user: CollegeUser, *, password: str, actor_id, request_meta: dict
    ) -> None:
        if not user.check_password(password):
            raise ValidationException("Password confirmation is incorrect.")
        self.sessions.revoke_other_sessions(domain=COLLEGE_DOMAIN, user_id=user.pk)
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
            domain=COLLEGE_DOMAIN,
            user_id=user.pk,
            event_type="account.deleted",
            title="Account deletion requested",
            description="Your institution recruiter account was deactivated and scheduled for removal.",
            ip_address=request_meta.get("ip_address"),
        )

    def build_account_info(self, user: CollegeUser) -> dict:
        settings = self.get_or_create_settings(user)
        attempt = (
            LoginAttempt.objects.filter(
                domain=COLLEGE_DOMAIN, user_id=user.pk, result="success"
            )
            .order_by("-attempted_at")
            .first()
        )
        full_name = settings.full_name or user.email.split("@")[0]
        return {
            "full_name": full_name,
            "first_name": settings.first_name,
            "last_name": settings.last_name,
            "email": user.email,
            "phone": settings.phone or "",
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
    def build_notification_prefs(settings: CollegeAccountSettings) -> dict:
        return {field: getattr(settings, field) for field in NOTIFICATION_FIELDS}

    @staticmethod
    def build_privacy_settings(settings: CollegeAccountSettings) -> dict:
        return {field: getattr(settings, field) for field in PRIVACY_FIELDS}

    def build_security_summary(self, user: CollegeUser) -> dict:
        settings = self.get_or_create_settings(user)
        attempt = (
            LoginAttempt.objects.filter(
                domain=COLLEGE_DOMAIN, user_id=user.pk, result="success"
            )
            .order_by("-attempted_at")
            .first()
        )
        recommendations = []
        if not getattr(user, "email_verified", False):
            recommendations.append("Verify your email address.")
        if settings.phone and not settings.phone_verified:
            recommendations.append("Verify your mobile number.")
        if not settings.password_changed_at:
            recommendations.append("Update your password regularly.")
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
