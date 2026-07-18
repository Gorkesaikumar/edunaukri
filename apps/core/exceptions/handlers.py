from django.core.exceptions import (
    PermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.exceptions.api_exceptions import BaseAPIException
from apps.core.exceptions.domain_exceptions import DomainException


def _build_error_payload(code, message, details=None):
    payload = {
        "success": False,
        "code": code,
        "message": message,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def _extract_details(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"non_field_errors": data}
    return {"detail": [str(data)]}


def custom_exception_handler(exc, context):
    if isinstance(exc, DomainException):
        status_map = {
            "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
            "BUSINESS_LOGIC_ERROR": status.HTTP_400_BAD_REQUEST,
            "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
            "NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "CONFLICT": status.HTTP_409_CONFLICT,
            "RESUME_REQUIRED": status.HTTP_400_BAD_REQUEST,
        }
        return Response(
            _build_error_payload(exc.error_code, exc.message, exc.details),
            status=status_map.get(exc.error_code, status.HTTP_400_BAD_REQUEST),
        )

    response = exception_handler(exc, context)

    try:
        from django_ratelimit.exceptions import Ratelimited
        if isinstance(exc, Ratelimited):
            return Response(
                _build_error_payload("RATE_LIMITED", "Too many requests. Please slow down and try again later."),
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
    except ImportError:
        pass

    if isinstance(exc, BaseAPIException):
        return Response(
            _build_error_payload(
                exc.error_code,
                str(exc.detail),
                _extract_details(exc.detail)
                if isinstance(exc.detail, (dict, list))
                else None,
            ),
            status=exc.status_code,
        )

    if isinstance(exc, Http404):
        return Response(
            _build_error_payload("NOT_FOUND", "Resource not found."),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            _build_error_payload("PERMISSION_DENIED", str(exc) or "Permission denied."),
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            details = exc.message_dict
        elif hasattr(exc, "messages"):
            details = {"non_field_errors": exc.messages}
        else:
            details = {"detail": [str(exc)]}
        return Response(
            _build_error_payload("VALIDATION_ERROR", "Validation failed.", details),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if response is not None:
        code = "API_ERROR"
        if isinstance(exc, APIException):
            code = getattr(exc, "default_code", "API_ERROR").upper()
        return Response(
            _build_error_payload(code, str(exc.detail), _extract_details(exc.detail)),
            status=response.status_code,
        )

    return response
