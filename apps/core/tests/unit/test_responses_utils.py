import pytest

from apps.core.api.responses import (
    error_response,
    success_response,
    validation_error_response,
)
from apps.core.exceptions.domain_exceptions import ResourceNotFoundException
from apps.core.exceptions.handlers import custom_exception_handler
from apps.core.utils.pagination import (
    build_page_metadata,
    normalize_page,
    normalize_page_size,
)
from apps.core.utils.strings import normalize_email, slugify


def test_api_response_helpers():
    success = success_response({"ok": True})
    assert success.data["success"] is True
    err = error_response("TEST", "failed", status_code=400)
    assert err.data["error"]["code"] == "TEST"
    validation = validation_error_response({"field": ["invalid"]})
    assert validation.data["error"]["code"] == "VALIDATION_ERROR"


def test_domain_exception_handler():
    exc = ResourceNotFoundException("missing")
    response = custom_exception_handler(exc, {})
    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"


def test_pagination_helpers():
    assert normalize_page("0") == 1
    assert normalize_page_size("999") == 100
    meta = build_page_metadata(count=50, page=2, page_size=20)
    assert meta["has_next"] is True
    assert meta["has_previous"] is True


def test_string_helpers():
    assert normalize_email(" User@Example.COM ") == "user@example.com"
    assert slugify("Hello World!") == "hello-world"
