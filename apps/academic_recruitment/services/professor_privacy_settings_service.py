"""Update professor privacy settings with audit trail."""

from __future__ import annotations

from apps.accounts.profiles.constants.enums import ProfileVisibility
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_account_settings_service import (
    PRIVACY_FIELDS,
    ProfessorAccountSettingsService,
)
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService

PROFESSOR_DOMAIN = "professor"

VISIBILITY_UI_LABELS = {
    ProfileVisibility.PUBLIC: "Public",
    ProfileVisibility.EMPLOYERS_ONLY: "Institutions Only",
    ProfileVisibility.PRIVATE: "Private",
}

PRIVACY_FIELD_LABELS = {
    "profile_visibility": "Profile visibility",
    "allow_institution_cv_download": "CV download permission",
    "allow_institution_contact": "Institution contact permission",
    "show_email_on_profile": "Email visibility",
    "show_phone_on_profile": "Phone visibility",
}

PRIVACY_SUCCESS_MESSAGES = {
    "profile_visibility": "Profile visibility updated.",
    "allow_institution_cv_download": "CV download permission updated.",
    "allow_institution_contact": "Institution contact permission updated.",
    "show_email_on_profile": "Email visibility updated.",
    "show_phone_on_profile": "Phone visibility updated.",
}


class ProfessorPrivacySettingsService(BaseService):
    def __init__(self):
        self.account = ProfessorAccountSettingsService()
        self.audit = SecurityAuditService()

    @staticmethod
    def visibility_options_for_ui() -> list[tuple[str, str]]:
        return [
            (value, VISIBILITY_UI_LABELS.get(value, label))
            for value, label in ProfileVisibility.choices
        ]

    @BaseService.atomic
    def update(
        self, profile: ProfessorProfile, data: dict, *, request_meta: dict
    ) -> dict:
        if not data:
            raise ValidationException("No privacy fields provided.")

        settings = self.account.get_or_create_settings(profile)
        changed: list[tuple[str, object, object]] = []

        visibility = data.get("profile_visibility")
        if visibility is not None:
            if visibility not in ProfileVisibility.values:
                raise ValidationException("Invalid profile visibility value.")
            old_visibility = profile.profile_visibility
            if old_visibility != visibility:
                profile.profile_visibility = visibility
                profile.save(update_fields=["profile_visibility", "updated_at"])
                changed.append(("profile_visibility", old_visibility, visibility))

        settings_dirty = False
        for field in PRIVACY_FIELDS:
            if field not in data:
                continue
            old_val = getattr(settings, field)
            new_val = bool(data[field])
            if old_val != new_val:
                setattr(settings, field, new_val)
                settings_dirty = True
                changed.append((field, old_val, new_val))

        if settings_dirty:
            settings.save()

        if not changed:
            return {
                "data": self.account.build_privacy_settings(profile, settings),
                "message": "Privacy settings updated successfully.",
                "changed_fields": [],
            }

        ip_address = request_meta.get("ip_address")
        user_agent = request_meta.get("user_agent", "")
        for field, old_val, new_val in changed:
            self.audit.record(
                domain=PROFESSOR_DOMAIN,
                user_id=profile.user_id,
                event_type=f"privacy.{field}.changed",
                title=f"{PRIVACY_FIELD_LABELS[field]} updated",
                description=f"Changed from {old_val} to {new_val}.",
                ip_address=ip_address,
                metadata={
                    "field": field,
                    "previous_value": old_val,
                    "new_value": new_val,
                    "user_agent": user_agent,
                },
            )

        changed_fields = [field for field, _, _ in changed]
        if len(changed) == 1:
            message = PRIVACY_SUCCESS_MESSAGES.get(
                changed[0][0], "Privacy settings updated successfully."
            )
        else:
            message = "Privacy settings updated successfully."

        return {
            "data": self.account.build_privacy_settings(profile, settings),
            "message": message,
            "changed_fields": changed_fields,
        }
