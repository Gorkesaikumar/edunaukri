"""Institution settings portal — Account & Security Center context."""

from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.models.college_user import CollegeUser
from apps.academic_recruitment.services.college_account_settings_service import (
    NOTIFICATION_FIELDS,
    PRIVACY_FIELDS,
    CollegeAccountSettingsService,
)
from apps.authentication.services.connected_accounts_service import (
    ConnectedAccountsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.core.services.base import BaseService

COLLEGE_DOMAIN = "college"


@dataclass
class CollegeSettingsContext:
    account: dict
    notifications: dict
    privacy: dict
    security: dict
    connected_accounts: list[dict]
    sessions: list[dict]
    audit_log: list[dict]
    api_urls: dict


class CollegeSettingsPortalService(BaseService):
    NOTIFICATION_LABELS = {
        "notify_new_applications": "New Applications",
        "notify_application_updates": "Application Status Updates",
        "notify_interviews": "Interview Notifications",
        "notify_offers": "Offer Notifications",
        "notify_vacancy_updates": "Vacancy Updates",
        "notify_verification_alerts": "Verification Alerts",
        "notify_faculty_messages": "Faculty Messages",
        "notify_marketing": "Marketing Emails",
        "notify_security_alerts": "Security Alerts",
        "notify_weekly_digest": "Weekly Recruitment Digest",
    }

    PRIVACY_LABELS = {
        "show_email_to_applicants": "Show Email to Applicants",
        "show_phone_to_applicants": "Show Phone to Applicants",
        "allow_direct_applicant_contact": "Allow Direct Applicant Contact",
    }

    def __init__(self):
        self.account = CollegeAccountSettingsService()
        self.sessions = SessionManagementService()
        self.audit = SecurityAuditService()
        self.connected = ConnectedAccountsService()

    def build(self, user: CollegeUser, *, request) -> CollegeSettingsContext:
        settings = self.account.get_or_create_settings(user)
        current_key = self.sessions.current_session_key_from_request(request)
        cu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        return CollegeSettingsContext(
            account=self.account.build_account_info(user),
            notifications=self.account.build_notification_prefs(settings),
            privacy=self.account.build_privacy_settings(settings),
            security=self.account.build_security_summary(user),
            connected_accounts=self.connected.list_for_user(
                domain=COLLEGE_DOMAIN,
                user_id=user.pk,
                settings_return_url=cu("college_settings"),
            ),
            sessions=self.sessions.list_sessions(
                domain=COLLEGE_DOMAIN,
                user_id=user.pk,
                current_session_key=current_key,
            ),
            audit_log=[
                self.audit.serialize_event(e)
                for e in self.audit.list_activity_for_user(
                    domain=COLLEGE_DOMAIN, user_id=user.pk, limit=15
                )
            ],
            api_urls={
                "account": cu("college_settings_account_api"),
                "password": cu("college_settings_password_api"),
                "notifications": cu("college_settings_notifications_api"),
                "privacy": cu("college_settings_privacy_api"),
                "sessions": cu("college_settings_sessions_api"),
                "revoke_others": cu("college_settings_revoke_sessions_api"),
                "delete_account": cu("college_settings_delete_api"),
                "audit": cu("college_settings_audit_api"),
                "connected": cu("college_settings_connected_api"),
            },
        )

    def notification_toggles(self, notifications: dict) -> list[dict]:
        return [
            {
                "key": key,
                "label": self.NOTIFICATION_LABELS[key],
                "enabled": notifications.get(key, False),
            }
            for key in NOTIFICATION_FIELDS
        ]

    def privacy_toggles(self, privacy: dict) -> list[dict]:
        return [
            {
                "key": key,
                "label": self.PRIVACY_LABELS[key],
                "enabled": privacy.get(key, False),
            }
            for key in PRIVACY_FIELDS
        ]
