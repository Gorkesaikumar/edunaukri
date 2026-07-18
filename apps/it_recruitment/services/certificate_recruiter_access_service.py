"""Recruiter and admin read-only access to candidate certificates."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from apps.applications.models import JobApplication
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.documents.models import StoredFile
from apps.it_recruitment.models import JobSeekerCertification
from apps.it_recruitment.selectors.profile_selector import JobSeekerProfileSelector
from apps.it_recruitment.services.certificate_management_service import (
    CertificateManagementService,
)
from apps.notifications.services.outbox_processor import OutboxProcessorService


class CertificateRecruiterAccessService(BaseService):
    """Authorize recruiters/admins to view certificates for application candidates."""

    def list_for_application(self, application: JobApplication, *, actor) -> list[dict]:
        self._ensure_view_access(application, actor)
        certs = (
            application.job_seeker.certifications.filter(is_deleted=False)
            .select_related("certificate_file")
            .order_by("-issue_date", "-created_at")
        )
        return [self._serialize(application, cert) for cert in certs]

    def resolve_certificate_file(
        self, application: JobApplication, certification_id, *, actor
    ) -> tuple[JobSeekerCertification, StoredFile]:
        self._ensure_view_access(application, actor)
        cert = (
            application.job_seeker.certifications.filter(
                pk=certification_id, is_deleted=False
            )
            .select_related("certificate_file")
            .first()
        )
        if not cert or not cert.certificate_file_id or not cert.certificate_file:
            raise PermissionDenied("Certificate file not available.")
        return cert, cert.certificate_file

    def record_recruiter_download(
        self, application: JobApplication, cert: JobSeekerCertification, *, actor
    ) -> None:
        if not self._is_recruiter_actor(application, actor):
            return
        recruiter_name = getattr(actor, "full_name", None) or "A recruiter"
        self._notify_candidate(
            application,
            event_type="certificate.downloaded",
            title="Recruiter downloaded your certificate",
            body=f'{recruiter_name} downloaded "{cert.name}" for {application.job_title_snapshot}.',
        )

    def record_recruiter_preview(
        self, application: JobApplication, cert: JobSeekerCertification, *, actor
    ) -> None:
        if not self._is_recruiter_actor(application, actor):
            return
        self._notify_candidate(
            application,
            event_type="certificate.viewed",
            title="Recruiter viewed your certificate",
            body=f'A recruiter previewed "{cert.name}" for {application.job_title_snapshot}.',
        )

    def _serialize(
        self, application: JobApplication, cert: JobSeekerCertification
    ) -> dict:
        status = CertificateManagementService.resolve_status(cert)
        ext = ""
        if cert.certificate_file and cert.certificate_file.original_filename:
            parts = cert.certificate_file.original_filename.rsplit(".", 1)
            if len(parts) == 2:
                ext = parts[1].lower()
        has_file = bool(cert.certificate_file_id)
        return {
            "id": str(cert.id),
            "name": cert.name,
            "issuing_organization": cert.issuing_organization,
            "category": cert.category,
            "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
            "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
            "credential_id": cert.credential_id,
            "credential_url": cert.credential_url,
            "is_verified": cert.is_verified,
            "status_key": status.key,
            "status_label": status.label,
            "has_file": has_file,
            "file_name": cert.certificate_file.original_filename
            if cert.certificate_file
            else "",
            "file_type": ext.upper() if ext else "",
            "is_pdf": ext == "pdf",
            "is_image": ext in {"jpg", "jpeg", "png"},
            "download_url": reverse(
                "job-application-certificate-download",
                kwargs={"application_id": application.pk, "certification_id": cert.pk},
            )
            if has_file
            else None,
            "preview_url": reverse(
                "job-application-certificate-preview",
                kwargs={"application_id": application.pk, "certification_id": cert.pk},
            )
            if has_file
            else None,
        }

    @staticmethod
    def _ensure_view_access(application: JobApplication, actor) -> None:
        try:
            ApplicationAuthorizationService().ensure_can_view_it_application(
                application, actor
            )
        except PermissionDeniedException as exc:
            raise PermissionDenied(str(exc)) from exc

    @staticmethod
    def is_recruiter_actor(application: JobApplication, actor) -> bool:
        seeker = JobSeekerProfileSelector().for_user(actor)
        return not seeker or seeker.pk != application.job_seeker_id

    @staticmethod
    def _is_recruiter_actor(application: JobApplication, actor) -> bool:
        return CertificateRecruiterAccessService.is_recruiter_actor(application, actor)

    @staticmethod
    def _notify_candidate(
        application: JobApplication, *, event_type: str, title: str, body: str
    ) -> None:
        OutboxService().publish(
            domain=DomainType.IT,
            event_type=event_type,
            aggregate_type="it_job_application",
            aggregate_id=application.pk,
            payload={
                "recipient_domain": "it",
                "recipient_id": str(application.job_seeker.user_id),
                "title": title,
                "body": body,
            },
        )
        try:
            OutboxProcessorService().process_batch(limit=5)
        except Exception:
            pass
