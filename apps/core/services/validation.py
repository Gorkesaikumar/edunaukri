from django.core.exceptions import ValidationError as DjangoValidationError

from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService


class ValidationService(BaseService):
    """Centralized validation orchestration for services."""

    def validate(self, *, validator, value, **context):
        try:
            if callable(validator):
                result = validator(value, **context)
            elif hasattr(validator, "validate"):
                result = validator.validate(value, **context)
            else:
                raise TypeError("Validator must be callable or expose validate().")
        except DjangoValidationError as exc:
            details = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"detail": exc.messages}
            )
            raise ValidationException(
                message="Validation failed.", details=details
            ) from exc
        return result if result is not None else value

    def validate_many(self, validators: list, *, data: dict) -> None:
        errors = {}
        for field, validator in validators:
            try:
                self.validate(validator=validator, value=data.get(field), field=field)
            except ValidationException as exc:
                errors[field] = exc.details or exc.message
        if errors:
            raise ValidationException(message="Validation failed.", details=errors)
