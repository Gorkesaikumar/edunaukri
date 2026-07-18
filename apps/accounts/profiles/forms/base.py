from django import forms

from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_validation_service import (
    ProfileValidationService,
)
from apps.core.exceptions.domain_exceptions import ValidationException


class BaseProfileForm(forms.Form):
    profile_type: ProfileType | None = None

    def __init__(self, *args, is_create: bool = True, **kwargs):
        self._is_create = is_create
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self.errors or self.profile_type is None:
            return cleaned
        try:
            if self.is_create:
                return ProfileValidationService().validate_create(
                    self.profile_type, cleaned
                )
            return ProfileValidationService().validate_update(
                self.profile_type, cleaned
            )
        except ValidationException as exc:
            detail = exc.message
            if isinstance(exc.details, dict):
                for field, message in exc.details.items():
                    if field in self.fields:
                        self.add_error(field, message)
                    else:
                        self.add_error(
                            None, message if isinstance(message, str) else str(message)
                        )
            else:
                self.add_error(None, detail)
            return cleaned

    @property
    def is_create(self) -> bool:
        return self._is_create
