"""Unit tests for shared core infrastructure."""

import uuid
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.constants.enums import DomainType, RecordStatus
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.models.outbox_event import OutboxEvent
from apps.core.repositories.crud import CRUDRepository
from apps.core.services.business_rules import BusinessRule, BusinessRuleSet
from apps.core.services.storage import StorageService
from apps.core.services.validation import ValidationService
from apps.core.storage.local import LocalStorageBackend
from apps.core.validators.common import validate_email, validate_gst, validate_phone
from apps.core.validators.file import validate_image_upload


class OutboxRepository(CRUDRepository):
    model = OutboxEvent


@pytest.mark.django_db
def test_crud_repository_create_and_get():
    repo = OutboxRepository()
    event = repo.create(
        domain=DomainType.PLATFORM,
        event_type="test.event",
        aggregate_type="test",
        aggregate_id=uuid.uuid4(),
        payload={"k": "v"},
    )
    fetched = repo.get_by_id(event.pk)
    assert fetched.event_type == "test.event"


@pytest.mark.django_db
def test_crud_repository_not_found():
    repo = OutboxRepository()
    with pytest.raises(ResourceNotFoundException):
        repo.get_by_id(uuid.uuid4())


def test_validators_email_phone_gst():
    validate_email("user@example.com")
    validate_phone("9876543210")
    validate_gst("22AAAAA0000A1Z5")
    with pytest.raises(ValidationError):
        validate_email("not-an-email")


def test_image_upload_validator():
    file_obj = SimpleUploadedFile("logo.png", b"abc", content_type="image/png")
    validate_image_upload(file_obj)
    bad = SimpleUploadedFile(
        "logo.exe", b"abc", content_type="application/octet-stream"
    )
    with pytest.raises(ValidationError):
        validate_image_upload(bad)


def test_validation_service_wraps_errors():
    service = ValidationService()

    def _validator(value):
        raise ValidationError("bad")

    with pytest.raises(ValidationException):
        service.validate(validator=_validator, value="x")


class _AlwaysFailRule(BusinessRule):
    message = "failed"

    def is_satisfied(self, context):
        return False


def test_business_rule_set():
    with pytest.raises(BusinessLogicException):
        BusinessRuleSet([_AlwaysFailRule()]).evaluate({})


def test_local_storage_backend(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    backend = LocalStorageBackend()
    path = backend.save(relative_path="test/sample.txt", content=b"hello")
    assert backend.exists(relative_path=path)
    assert backend.open(relative_path=path).read_text() == "hello"
    backend.delete(relative_path=path)
    assert not backend.exists(relative_path=path)


def test_storage_service_wrapper(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    service = StorageService()
    saved = service.save_bytes(relative_path="wrapped/file.bin", content=b"data")
    assert service.file_exists(relative_path=saved)
