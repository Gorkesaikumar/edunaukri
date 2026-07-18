"""Middleware for handling rate limit exceptions across HTML and JSON endpoints."""

import logging
from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.exceptions import Ratelimited

logger = logging.getLogger(__name__)


class RatelimitExceptionMiddleware:
    """Intercept Ratelimited exceptions and return appropriate HTTP 429 responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            logger.warning(
                "Rate limit exceeded: path=%s ip=%s user=%s",
                request.path,
                request.META.get("REMOTE_ADDR"),
                getattr(request.user, "pk", "anon"),
            )
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
        return None
