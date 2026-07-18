import logging

from django.http import JsonResponse

from apps.core.constants.error_messages import API_ERROR
from apps.core.logging.logger import get_logger

logger = get_logger(__name__)


class ExceptionMiddleware:
    """Catch unhandled exceptions for non-DRF views and return JSON envelope."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exc:
            try:
                from django_ratelimit.exceptions import Ratelimited
                if isinstance(exc, Ratelimited):
                    from django.shortcuts import render
                    logger.warning("Rate limit exceeded in non-DRF view: %s", request.path)
                    if (
                        "/api/" in request.path
                        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
                        or request.headers.get("Accept") == "application/json"
                        or request.content_type == "application/json"
                    ):
                        return JsonResponse(
                            {
                                "success": False,
                                "code": "RATE_LIMITED",
                                "message": "Too many requests. Please slow down and try again later.",
                                "errors": {
                                    "form": "Too many requests. Please slow down and try again later."
                                },
                            },
                            status=429,
                        )
                    return render(
                        request,
                        "429.html",
                        {"message": "Too many requests. Please slow down and try again later."},
                        status=429,
                    )
            except ImportError:
                pass

            logger.exception("unhandled_exception", exc_info=exc)
            
            if (
                "/api/" in request.path
                or request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Accept") == "application/json"
                or request.content_type == "application/json"
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "error": {"code": API_ERROR, "message": "Internal server error."},
                    },
                    status=500,
                )
            
            # For web requests, raise the exception to let Django's core handler render 500.html
            raise exc
