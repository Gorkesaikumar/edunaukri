from django.core.exceptions import ValidationError as DjangoValidationError

from apps.core.exceptions.domain_exceptions import ValidationException


def raise_if_invalid(condition: bool, message: str, *, details=None) -> None:
    if not condition:
        raise ValidationException(message, details=details)


def collect_field_errors(validators: dict, data: dict) -> dict:
    errors = {}
    for field, validator in validators.items():
        try:
            validator(data.get(field))
        except DjangoValidationError as exc:
            errors[field] = exc.messages
    return errors
