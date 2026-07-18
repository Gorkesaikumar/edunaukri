import logging
import time

from apps.core.logging.logger import get_logger
from apps.core.middleware.request_id import get_request_id

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """Structured request/response logging with correlation ID."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        request_id = get_request_id()
        logger.info(
            "request.start",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "remote_addr": request.META.get("REMOTE_ADDR"),
            },
        )
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request.finish",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
