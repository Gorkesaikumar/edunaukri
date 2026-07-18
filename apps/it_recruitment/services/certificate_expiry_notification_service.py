"""Scan job seeker certificates expiring soon and notify owners."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.it_recruitment.constants.certificate_enums import EXPIRING_SOON_DAYS
from apps.it_recruitment.models import JobSeekerCertification


class CertificateExpiryNotificationService(BaseService):
    """Notify seekers when certificates are approaching expiry."""

    def scan_and_notify(self, *, batch_size: int = 200) -> int:
        today = timezone.localdate()
        window_end = today + timedelta(days=EXPIRING_SOON_DAYS)
        qs = (
            JobSeekerCertification.objects.filter(
                is_deleted=False,
                expiry_date__gte=today,
                expiry_date__lte=window_end,
            )
            .select_related("job_seeker")
            .order_by("expiry_date")[:batch_size]
        )
        sent = 0
        for cert in qs:
            profile = cert.job_seeker
            OutboxService().publish(
                domain=DomainType.IT,
                event_type="certificate.expiring_soon",
                aggregate_type="job_seeker_certification",
                aggregate_id=cert.pk,
                payload={
                    "recipient_domain": "it",
                    "recipient_id": str(profile.user_id),
                    "title": "Certificate expiring soon",
                    "body": f"{cert.name} expires on {cert.expiry_date.strftime('%b %d, %Y')}.",
                    "certificate_id": str(cert.pk),
                },
            )
            sent += 1
        if sent:
            try:
                from apps.notifications.services.outbox_processor import (
                    OutboxProcessorService,
                )

                OutboxProcessorService().process_batch(limit=10)
            except Exception:
                pass
        return sent
