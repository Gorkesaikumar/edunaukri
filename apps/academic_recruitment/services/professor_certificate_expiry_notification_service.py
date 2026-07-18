"""Scan professor certificates expiring soon and notify owners."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.academic_recruitment.models import ProfessorCertification
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.it_recruitment.constants.certificate_enums import EXPIRING_SOON_DAYS


class ProfessorCertificateExpiryNotificationService(BaseService):
    """Notify faculty job seekers when certificates are approaching expiry."""

    def scan_and_notify(self, *, batch_size: int = 200) -> int:
        today = timezone.localdate()
        window_end = today + timedelta(days=EXPIRING_SOON_DAYS)
        qs = (
            ProfessorCertification.objects.filter(
                is_deleted=False,
                expiry_date__gte=today,
                expiry_date__lte=window_end,
            )
            .select_related("professor")
            .order_by("expiry_date")[:batch_size]
        )
        sent = 0
        for cert in qs:
            profile = cert.professor
            OutboxService().publish(
                domain=DomainType.FACULTY,
                event_type="certificate.expiring_soon",
                aggregate_type="professor_certification",
                aggregate_id=cert.pk,
                payload={
                    "recipient_domain": "professor",
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
