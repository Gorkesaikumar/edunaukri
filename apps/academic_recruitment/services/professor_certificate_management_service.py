"""Certificate upload, storage, and lifecycle management for faculty job seekers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.dateparse import parse_date
from django.utils import timezone

from apps.academic_recruitment.models import ProfessorCertification, ProfessorProfile
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.documents.constants.enums import StorageFileType
from apps.documents.models import StoredFile
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.constants.certificate_enums import (
    EXPIRING_SOON_DAYS,
    CertificateCategory,
)
from apps.notifications.services.outbox_processor import OutboxProcessorService


@dataclass
class CertificateStatus:
    key: str
    label: str
    badge: str


class ProfessorCertificateManagementService(BaseService):
    PROFILE_CONTRIBUTION = 6

    def __init__(self):
        self.storage = StorageService()
        self.completion = ProfessorProfileCompletionService()

    @BaseService.atomic
    def create(
        self, profile: ProfessorProfile, *, actor_id, data: dict, uploaded_file=None
    ) -> ProfessorCertification:
        payload = self._parse_payload(data)
        stored = (
            self._upload_file(profile, uploaded_file, actor_id)
            if uploaded_file
            else None
        )
        cert = ProfessorCertification.objects.create(
            professor=profile,
            created_by_id=actor_id,
            certificate_file=stored,
            **payload,
        )
        self._after_change(
            profile,
            event="certificate.uploaded",
            title="Certificate uploaded",
            body=f"{cert.name} was added to your profile.",
        )
        return cert

    @BaseService.atomic
    def update(
        self, profile: ProfessorProfile, cert_id, *, actor_id, data: dict
    ) -> ProfessorCertification:
        cert = self._get_owned(profile, cert_id)
        for key, value in self._parse_payload(
            data, partial=True, existing=cert
        ).items():
            setattr(cert, key, value)
        cert.updated_by_id = actor_id
        cert.save()
        self._after_change(
            profile,
            event="certificate.updated",
            title="Certificate updated",
            body=f"{cert.name} was updated.",
        )
        return cert

    @BaseService.atomic
    def replace_file(
        self, profile: ProfessorProfile, cert_id, *, actor_id, uploaded_file
    ) -> ProfessorCertification:
        cert = self._get_owned(profile, cert_id)
        previous = cert.certificate_file
        stored = self._upload_file(profile, uploaded_file, actor_id)
        cert.certificate_file = stored
        cert.save(update_fields=["certificate_file", "updated_at"])
        if previous and previous.pk != stored.pk:
            self.storage.remove_stored_file(previous)
        self._after_change(
            profile,
            event="certificate.updated",
            title="Certificate file replaced",
            body=f"The file for {cert.name} was replaced.",
        )
        return cert

    @BaseService.atomic
    def delete(self, profile: ProfessorProfile, cert_id, *, actor_id) -> None:
        cert = self._get_owned(profile, cert_id)
        name = cert.name
        if cert.certificate_file_id:
            self.storage.remove_stored_file(cert.certificate_file)
        cert.delete()
        self._after_change(
            profile,
            event="certificate.deleted",
            title="Certificate deleted",
            body=f"{name} was removed from your profile.",
        )

    def get_file(self, profile: ProfessorProfile, cert_id) -> StoredFile:
        cert = self._get_owned(profile, cert_id)
        if not cert.certificate_file_id or not cert.certificate_file:
            raise ResourceNotFoundException("Certificate file not found.")
        return cert.certificate_file

    @staticmethod
    def resolve_status(cert: ProfessorCertification) -> CertificateStatus:
        if cert.is_verified:
            return CertificateStatus("verified", "Verified", "jsd-cert-badge--verified")
        if not cert.expiry_date:
            return CertificateStatus(
                "lifetime", "Lifetime Certificate", "jsd-cert-badge--lifetime"
            )
        today = timezone.localdate()
        if cert.expiry_date < today:
            return CertificateStatus("expired", "Expired", "jsd-cert-badge--expired")
        if cert.expiry_date <= today + timedelta(days=EXPIRING_SOON_DAYS):
            return CertificateStatus(
                "expiring", "Expiring Soon", "jsd-cert-badge--expiring"
            )
        return CertificateStatus("active", "Active", "jsd-cert-badge--active")

    def _upload_file(self, profile, uploaded_file, actor_id) -> StoredFile:
        try:
            return self.storage.upload(
                uploaded_file=uploaded_file,
                domain=DomainType.FACULTY,
                file_type=StorageFileType.CERTIFICATE,
                owner_type="professor_certification",
                owner_id=profile.pk,
                uploaded_by_id=actor_id,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise ValidationException(message) from exc

    def _parse_payload(
        self, data: dict, *, partial: bool = False, existing=None
    ) -> dict:
        payload: dict = {}
        if "name" in data or not partial:
            name = (data.get("name") or data.get("certification_name") or "").strip()
            if not name and not partial:
                raise ValidationException("Certificate name is required.")
            if name:
                payload["name"] = name
        if "issuing_organization" in data or "organization" in data or not partial:
            org = (
                data.get("issuing_organization") or data.get("organization") or ""
            ).strip()
            if org or not partial:
                payload["issuing_organization"] = org
        if "category" in data or not partial:
            cat = (data.get("category") or CertificateCategory.OTHER).strip().lower()
            if cat not in CertificateCategory.values:
                cat = CertificateCategory.OTHER
            payload["category"] = cat
        if "issue_date" in data or not partial:
            raw = data.get("issue_date")
            payload["issue_date"] = parse_date(raw) if raw else None
        if "expiry_date" in data:
            raw = data.get("expiry_date")
            payload["expiry_date"] = parse_date(raw) if raw else None
        elif not partial:
            payload["expiry_date"] = None
        if "credential_id" in data or not partial:
            payload["credential_id"] = (data.get("credential_id") or "").strip()
        if "credential_url" in data or not partial:
            payload["credential_url"] = (data.get("credential_url") or "").strip()
        if (
            payload.get("expiry_date")
            and payload.get("issue_date")
            and payload["expiry_date"] < payload["issue_date"]
        ):
            raise ValidationException("Expiry date cannot be before issue date.")
        return payload

    def _get_owned(self, profile, cert_id) -> ProfessorCertification:
        cert = (
            profile.certifications.filter(pk=cert_id, is_deleted=False)
            .select_related("certificate_file")
            .first()
        )
        if not cert:
            raise ResourceNotFoundException("Certificate not found.")
        return cert

    def _after_change(self, profile, *, event: str, title: str, body: str) -> None:
        before = profile.profile_completeness
        self.completion.recalculate(profile)
        profile.refresh_from_db()
        if profile.profile_completeness > before:
            self._notify(
                profile,
                event_type="profile.completion_increased",
                title="Profile completion increased",
                body=f"Your profile is now {profile.profile_completeness}% complete.",
            )
        self._notify(profile, event_type=event, title=title, body=body)

    @staticmethod
    def _notify(profile, *, event_type: str, title: str, body: str) -> None:
        OutboxService().publish(
            domain=DomainType.FACULTY,
            event_type=event_type,
            aggregate_type="professor_profile",
            aggregate_id=profile.pk,
            payload={
                "recipient_domain": "professor",
                "recipient_id": str(profile.user_id),
                "title": title,
                "body": body,
            },
        )
        try:
            OutboxProcessorService().process_batch(limit=5)
        except Exception:
            pass
