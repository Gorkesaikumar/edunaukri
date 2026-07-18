"""Professor settings portal — Account & Security Center context."""

from __future__ import annotations

from dataclasses import dataclass

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_account_settings_service import (
    NOTIFICATION_FIELDS,
    ProfessorAccountSettingsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.connected_accounts_service import (
    ConnectedAccountsService,
)
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.core.services.base import BaseService

PROFESSOR_DOMAIN = "professor"


@dataclass
class ProfessorSettingsContext:
    account: dict
    notifications: dict
    privacy: dict
    security: dict
    connected_accounts: list[dict]
    sessions: list[dict]
    audit_log: list[dict]
    api_urls: dict


class ProfessorSettingsPortalService(BaseService):
    NOTIFICATION_LABELS = {
        "notify_vacancy_recommendations": "Vacancy Recommendations",
        "notify_institution_messages": "Institution Messages",
        "notify_application_updates": "Application Updates",
        "notify_interviews": "Interview Notifications",
        "notify_offers": "Offer Notifications",
        "notify_marketing": "Marketing Emails",
        "notify_security_alerts": "Security Alerts",
        "notify_profile_views": "Profile View Notifications",
        "notify_cv_downloads": "CV Download Notifications",
        "notify_weekly_digest": "Weekly Vacancy Digest",
    }

    PRIVACY_LABELS = {
        "allow_institution_cv_download": "Allow Institutions to Download CV",
        "allow_institution_contact": "Allow Institutions to Contact Me",
        "show_email_on_profile": "Show Email Address",
        "show_phone_on_profile": "Show Phone Number",
    }

    def __init__(self):
        self.account = ProfessorAccountSettingsService()
        self.sessions = SessionManagementService()
        self.audit = SecurityAuditService()
        self.connected = ConnectedAccountsService()

    def build(self, profile: ProfessorProfile, *, request) -> ProfessorSettingsContext:
        user = profile.user
        settings = self.account.get_or_create_settings(profile)
        current_key = self.sessions.current_session_key_from_request(request)
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        return ProfessorSettingsContext(
            account=self.account.build_account_info(profile),
            notifications=self.account.build_notification_prefs(settings),
            privacy=self.account.build_privacy_settings(profile, settings),
            security=self.account.build_security_summary(profile),
            connected_accounts=self.connected.list_for_user(
                domain=PROFESSOR_DOMAIN,
                user_id=profile.user_id,
                settings_return_url=pu("professor_settings"),
            ),
            sessions=self.sessions.list_sessions(
                domain=PROFESSOR_DOMAIN,
                user_id=profile.user_id,
                current_session_key=current_key,
            ),
            audit_log=[
                self.audit.serialize_event(e)
                for e in self.audit.list_activity_for_user(
                    domain=PROFESSOR_DOMAIN, user_id=profile.user_id, limit=15
                )
            ],
            api_urls={
                "account": pu("professor_settings_account_api"),
                "password": pu("professor_settings_password_api"),
                "notifications": pu("professor_settings_notifications_api"),
                "privacy": pu("professor_settings_privacy_api"),
                "sessions": pu("professor_settings_sessions_api"),
                "revoke_others": pu("professor_settings_revoke_sessions_api"),
                "delete_account": pu("professor_settings_delete_api"),
                "audit": pu("professor_settings_audit_api"),
                "connected": pu("professor_settings_connected_api"),
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
        from apps.academic_recruitment.services.professor_account_settings_service import (
            PRIVACY_FIELDS,
        )

        return [
            {
                "key": key,
                "label": self.PRIVACY_LABELS[key],
                "enabled": privacy.get(key, False),
            }
            for key in PRIVACY_FIELDS
        ]
