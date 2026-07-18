from apps.core.exceptions.api_exceptions import (
    BaseAPIException,
    ConflictAPIError,
    NotFoundAPIError,
    PermissionDeniedAPIError,
    ServiceUnavailableAPIError,
    ValidationAPIError,
)
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    DomainException,
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
)


def custom_exception_handler(exc, context):
    from apps.core.exceptions.handlers import custom_exception_handler as _handler

    return _handler(exc, context)


__all__ = [
    "BaseAPIException",
    "ValidationAPIError",
    "NotFoundAPIError",
    "PermissionDeniedAPIError",
    "ConflictAPIError",
    "ServiceUnavailableAPIError",
    "DomainException",
    "ValidationException",
    "BusinessLogicException",
    "PermissionDeniedException",
    "ResourceNotFoundException",
    "ConflictException",
    "custom_exception_handler",
]
