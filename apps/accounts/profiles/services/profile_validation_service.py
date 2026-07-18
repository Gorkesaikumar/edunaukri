from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.validators import profile_validator as validators
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.core.services.validation import ValidationService
from apps.documents.models import StoredFile
from apps.documents.selectors.stored_file_selector import StoredFileSelector


class ProfileValidationService(BaseService):
    """Centralized profile field validation."""

    FILE_FIELDS = frozenset(
        {
            "resume_file_id",
            "profile_photo_id",
            "profile_image_id",
            "cv_file_id",
            "logo_file_id",
        }
    )

    def __init__(self):
        self.validation = ValidationService()

    def validate_create(self, profile_type: ProfileType, data: dict) -> dict:
        if profile_type in (
            ProfileType.JOB_SEEKER,
            ProfileType.RECRUITER,
            ProfileType.PROFESSOR,
        ):
            if (
                not data.get("first_name", "").strip()
                or not data.get("last_name", "").strip()
            ):
                raise ValidationException("First name and last name are required.")
        if profile_type == ProfileType.COLLEGE and not data.get("name", "").strip():
            raise ValidationException("Institution name is required.")
        return self.validate_update(profile_type, data, is_create=True)

    def validate_update(
        self, profile_type: ProfileType, data: dict, *, is_create: bool = False
    ) -> dict:
        cleaned = dict(data)

        if "phone" in cleaned and cleaned["phone"]:
            cleaned["phone"] = self.validation.validate(
                validator=validators.validate_profile_phone, value=cleaned["phone"]
            )
        if "official_email" in cleaned and cleaned["official_email"]:
            cleaned["official_email"] = self.validation.validate(
                validator=validators.validate_profile_email,
                value=cleaned["official_email"],
            )
        if "contact_email" in cleaned and cleaned["contact_email"]:
            cleaned["contact_email"] = self.validation.validate(
                validator=validators.validate_profile_email,
                value=cleaned["contact_email"],
            )
        if "contact_phone" in cleaned and cleaned["contact_phone"]:
            cleaned["contact_phone"] = self.validation.validate(
                validator=validators.validate_profile_phone,
                value=cleaned["contact_phone"],
            )

        for url_field in (
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "personal_website",
            "website_url",
        ):
            if url_field in cleaned and cleaned[url_field]:
                cleaned[url_field] = self.validation.validate(
                    validator=validators.validate_profile_url, value=cleaned[url_field]
                )

        for salary_field in ("expected_salary", "current_salary"):
            if salary_field in cleaned:
                cleaned[salary_field] = validators.validate_salary(
                    cleaned[salary_field], field_name=salary_field
                )

        for exp_field in (
            "experience_years",
            "teaching_experience_years",
            "industry_experience_years",
        ):
            if exp_field in cleaned:
                cleaned[exp_field] = validators.validate_experience_years(
                    cleaned[exp_field]
                )

        if "notice_period_days" in cleaned:
            cleaned["notice_period_days"] = validators.validate_notice_period_days(
                cleaned["notice_period_days"]
            )

        if "highest_qualification" in cleaned and cleaned["highest_qualification"]:
            cleaned["highest_qualification"] = validators.validate_qualification_name(
                cleaned["highest_qualification"]
            )

        for file_field in self.FILE_FIELDS:
            if file_field in cleaned and cleaned[file_field]:
                self._validate_file_reference(cleaned[file_field])

        return cleaned

    def _validate_file_reference(self, file_id) -> StoredFile:
        stored = StoredFileSelector().get_active(file_id)
        if not stored:
            raise ValidationException("Referenced file was not found.")
        return stored
