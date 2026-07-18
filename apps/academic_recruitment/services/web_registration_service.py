"""Faculty domain web registration — professor and institution signup."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.authentication.services.registration_service import RegistrationService
from apps.authentication.services.web_registration_finalize import (
    WebRegistrationFinalizeService,
)
from apps.authentication.validators.password_validator import validate_password_strength
from apps.core.services.base import BaseService
from apps.core.validators.common import validate_email, validate_phone
from apps.it_recruitment.services.web_registration_service import (
    normalize_mobile,
    split_full_name,
)

logger = logging.getLogger(__name__)


class FacultyWebRegistrationService(BaseService):
    """Orchestrates faculty signup for the web UI."""

    @transaction.atomic
    def register_professor(self, request, *, data: dict):
        errors = self._validate_professor(data)
        if errors:
            raise ValidationError(errors)

        email = data["email"].lower().strip()
        user = RegistrationService().register_professor(
            email=email, password=data["password"]
        )
        first_name, last_name = split_full_name(data["full_name"])
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.PROFESSOR,
            data={
                "first_name": first_name,
                "last_name": last_name,
                "phone": normalize_mobile(data["mobile"]),
            },
        )
        return self._finalize(
            request, user=user, domain="professor", password=data["password"]
        )

    @transaction.atomic
    def register_institution(self, request, *, data: dict):
        errors = self._validate_institution(data)
        if errors:
            raise ValidationError(errors)

        email = data["email"].lower().strip()
        user = RegistrationService().register_college_user(
            email=email, password=data["password"]
        )
        mobile = normalize_mobile(data["mobile"])
        ProfileService().create_profile(
            user=user,
            profile_type=ProfileType.COLLEGE,
            data={
                "name": data["institution_name"].strip(),
                "contact_email": email,
                "contact_phone": mobile,
            },
        )
        return self._finalize(
            request, user=user, domain="college", password=data["password"]
        )

    def email_exists(self, email: str, *, role: str) -> bool:
        email = email.lower().strip()
        if role == "institution":
            return CollegeUser.objects.filter(email=email, is_deleted=False).exists()
        return ProfessorUser.objects.filter(email=email, is_deleted=False).exists()

    def mobile_exists(self, mobile: str, *, role: str) -> bool:
        from apps.academic_recruitment.models import ProfessorProfile
        from apps.colleges.models import College

        digits = normalize_mobile(mobile)
        if not digits:
            return False
        if role == "institution":
            return College.objects.filter(
                contact_phone=digits, is_deleted=False
            ).exists()
        return ProfessorProfile.objects.filter(phone=digits, is_deleted=False).exists()

    @staticmethod
    def _finalize(request, *, user, domain: str, password: str):
        from apps.authentication.services.portal_url_service import PortalURLService

        return WebRegistrationFinalizeService().finalize(
            request,
            user=user,
            domain=domain,
            password=password,
            dashboard_url_resolver=PortalURLService.dashboard_for_user,
        )

    def _validate_professor(self, data: dict) -> dict:
        errors: dict[str, str] = {}
        if not (data.get("full_name") or "").strip():
            errors["full_name"] = "Full name is required."

        email_raw = (data.get("email") or "").strip()
        if not email_raw:
            errors["email"] = "Email address is required."
        elif len(email_raw) > 254:
            errors["email"] = "Email address cannot exceed 254 characters."
        else:
            try:
                validate_email(email_raw)
                if self.email_exists(email_raw.lower(), role="seeker"):
                    errors["email"] = "An account with this email already exists."
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        if not (data.get("mobile") or "").strip():
            errors["mobile"] = "Mobile number is required."
        else:
            try:
                validate_phone(data["mobile"])
                if self.mobile_exists(data["mobile"], role="seeker"):
                    errors["mobile"] = "This mobile number is already registered."
            except ValidationError:
                errors["mobile"] = "Enter a valid mobile number."

        errors.update(
            self._validate_password(data.get("password"), data.get("confirm_password"))
        )
        return errors

    def _validate_institution(self, data: dict) -> dict:
        errors: dict[str, str] = {}

        if not (data.get("institution_name") or "").strip():
            errors["institution_name"] = "Institution name is required."
        if not (data.get("rep_name") or "").strip():
            errors["rep_name"] = "Representative name is required."

        email_raw = (data.get("email") or "").strip()
        if not email_raw:
            errors["email"] = "Email address is required."
        elif len(email_raw) > 254:
            errors["email"] = "Email address cannot exceed 254 characters."
        else:
            try:
                validate_email(email_raw)
                if self.email_exists(email_raw.lower(), role="institution"):
                    errors["email"] = "An account with this email already exists."
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        if not (data.get("mobile") or "").strip():
            errors["mobile"] = "Mobile number is required."
        else:
            try:
                validate_phone(data["mobile"])
                if self.mobile_exists(data["mobile"], role="institution"):
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
