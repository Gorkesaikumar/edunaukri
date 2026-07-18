from rest_framework.exceptions import APIException


class BaseAPIException(APIException):
    error_code = "API_ERROR"

    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code or self.error_code)


class ValidationAPIError(BaseAPIException):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    default_detail = "Validation failed."


class NotFoundAPIError(BaseAPIException):
    status_code = 404
    error_code = "NOT_FOUND"
    default_detail = "Resource not found."


class PermissionDeniedAPIError(BaseAPIException):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    default_detail = "Permission denied."


class ConflictAPIError(BaseAPIException):
    status_code = 409
    error_code = "CONFLICT"
    default_detail = "Resource conflict."


class ServiceUnavailableAPIError(BaseAPIException):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    default_detail = "Service temporarily unavailable."
