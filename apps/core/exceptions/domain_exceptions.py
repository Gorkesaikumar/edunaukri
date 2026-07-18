class DomainException(Exception):
    """Base class for domain-layer exceptions raised by services."""

    error_code = "DOMAIN_ERROR"

    def __init__(self, message: str, *, details: dict | list | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationException(DomainException):
    error_code = "VALIDATION_ERROR"


class BusinessLogicException(DomainException):
    error_code = "BUSINESS_LOGIC_ERROR"


class PermissionDeniedException(DomainException):
    error_code = "PERMISSION_DENIED"


class ResourceNotFoundException(DomainException):
    error_code = "NOT_FOUND"


class ConflictException(DomainException):
    error_code = "CONFLICT"


class ResumeRequiredException(DomainException):
    error_code = "RESUME_REQUIRED"
