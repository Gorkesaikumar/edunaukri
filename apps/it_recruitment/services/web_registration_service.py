"""IT domain web registration — minimal account creation for the web UI."""

import logging
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.authentication.services.email_verification_service import (
    EmailVerificationService,
)
from apps.authentication.services.registration_service import RegistrationService
from apps.authentication.services.session_service import SessionService
from apps.authentication.validators.password_validator import validate_password_strength
from apps.core.validators.common import validate_email, validate_phone
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile

logger = logging.getLogger(__name__)

IT_MOBILE_EMAIL_DOMAIN = "it-mobile.edunaukri"


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " ".join(parts[1:])


def normalize_mobile(mobile: str) -> str:
    return re.sub(r"\D", "", mobile or "")


def recruiter_account_email(mobile: str) -> str:
    """Provisional login email derived from mobile — completed in dashboard later."""
    digits = normalize_mobile(mobile)
    return f"{digits}@{IT_MOBILE_EMAIL_DOMAIN}"


class ITWebRegistrationService:
    """Orchestrates streamlined IT signup for the web UI."""

    @transaction.atomic
    def register_job_seeker(self, request, *, data: dict):
        errors = self._validate_job_seeker(data)
        if errors:
            raise ValidationError(errors)

        email = data["email"].lower().strip()
        user = RegistrationService().register_job_seeker(
            email=email, password=data["password"]
        )

        first_name, last_name = split_full_name(data["full_name"])
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.JOB_SEEKER,
            data={
                "first_name": first_name,
                "last_name": last_name,
                "phone": normalize_mobile(data["mobile"]),
            },
        )

        return self._finalize_registration(
            request, user=user, domain="it", password=data["password"]
        )

    @transaction.atomic
    def register_recruiter(self, request, *, data: dict):
        errors = self._validate_recruiter(data)
        if errors:
            raise ValidationError(errors)

        mobile = normalize_mobile(data["mobile"])
        email = recruiter_account_email(mobile)
        if self.email_exists(email):
            email = f"{mobile}.{uuid.uuid4().hex[:8]}@{IT_MOBILE_EMAIL_DOMAIN}"

        user = RegistrationService().register_recruiter(
            email=email, password=data["password"]
        )

        first_name, last_name = split_full_name(data["recruiter_name"])
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.RECRUITER,
            data={
                "first_name": first_name,
                "last_name": last_name,
                "phone": mobile,
                "company_association": data["company_name"].strip(),
            },
        )

        return self._finalize_registration(
            request, user=user, domain="it", password=data["password"]
        )

    def email_exists(self, email: str) -> bool:
        from apps.accounts.models.it_user import ITUser

        return ITUser.objects.filter(
            email=email.lower().strip(), is_deleted=False
        ).exists()

    def mobile_exists(self, mobile: str) -> bool:
        digits = normalize_mobile(mobile)
        if not digits:
            return False
        return (
            JobSeekerProfile.objects.filter(phone=digits, is_deleted=False).exists()
            or RecruiterProfile.objects.filter(phone=digits, is_deleted=False).exists()
        )

    def _finalize_registration(self, request, *, user, domain: str, password: str):
        from apps.authentication.services.portal_url_service import PortalURLService
        from apps.authentication.services.web_registration_finalize import (
            WebRegistrationFinalizeService,
        )

        return WebRegistrationFinalizeService().finalize(
            request,
            user=user,
            domain=domain,
            password=password,
            dashboard_url_resolver=PortalURLService.dashboard_for_user,
        )

    @staticmethod
    def _dashboard_url(user) -> str:
        from apps.authentication.services.portal_url_service import PortalURLService

        return PortalURLService.dashboard_for_user(user)

    def _validate_job_seeker(self, data: dict) -> dict:
        errors: dict[str, str] = {}

        if not (data.get("full_name") or "").strip():
            errors["full_name"] = "Full name is required."

        if not (data.get("email") or "").strip():
            errors["email"] = "Email address is required."
        else:
            try:
                validate_email(data["email"].strip())
                if self.email_exists(data["email"]):
                    errors["email"] = "An account with this email already exists."
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        if not (data.get("mobile") or "").strip():
            errors["mobile"] = "Mobile number is required."
        else:
            try:
                validate_phone(data["mobile"])
                if self.mobile_exists(data["mobile"]):
                    errors["mobile"] = "This mobile number is already registered."
            except ValidationError:
                errors["mobile"] = "Enter a valid mobile number."

        errors.update(
            self._validate_password(data.get("password"), data.get("confirm_password"))
        )
        return errors

    def _validate_recruiter(self, data: dict) -> dict:
        errors: dict[str, str] = {}

        if not (data.get("recruiter_name") or "").strip():
            errors["recruiter_name"] = "Recruiter name is required."
        if not (data.get("company_name") or "").strip():
            errors["company_name"] = "Company name is required."

        if not (data.get("mobile") or "").strip():
            errors["mobile"] = "Mobile number is required."
        else:
            try:
                validate_phone(data["mobile"])
                if self.mobile_exists(data["mobile"]):
                    errors["mobile"] = "This mobile number is already registered."
            except ValidationError:
                errors["mobile"] = "Enter a valid mobile number."

        errors.update(
            self._validate_password(data.get("password"), data.get("confirm_password"))
        )
        return errors

    @staticmethod
    def _validate_password(password: str | None, confirm: str | None) -> dict[str, str]:
        errors: dict[str, str] = {}
        if not password:
            errors["password"] = "Password is required."
            return errors
        try:
            validate_password_strength(password)
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            errors["password"] = message
        if not confirm:
            errors["confirm_password"] = "Please confirm your password."
        elif password and password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        return errors
