from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def validate_password_strength(password: str, *, user=None) -> None:
    validate_password(password, user=user)
