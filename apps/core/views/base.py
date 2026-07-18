from apps.core.api.responses import (
    error_response,
    paginated_response,
    success_response,
    validation_error_response,
)
from rest_framework.views import APIView


class EnvelopeAPIView(APIView):
    """Base API view that wraps responses in the standard success envelope."""

    def success_response(self, data, status=200):
        return success_response(data, status_code=status)

    def error_response(self, code, message, *, status=400, details=None):
        return error_response(code, message, status_code=status, details=details)

    def validation_error_response(self, details, *, message="Validation failed."):
        return validation_error_response(details, message=message)

    def paginated_response(self, **kwargs):
        return paginated_response(**kwargs)
