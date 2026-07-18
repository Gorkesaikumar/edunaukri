"""Celery tasks for interview reminders and maintenance."""

from __future__ import annotations

import logging

from celery import shared_task
from apps.core.tasks import BaseTask
from apps.core.utils.locking import redis_lock

from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    base=BaseTask,
    name="applications.send_interview_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
def send_interview_reminder_task(self, interview_id: str, reminder_type: str) -> bool:
    from apps.applications.models import JobApplicationInterview
    from apps.applications.services.application_event_service import (
        ApplicationEventService,
    )

    interview = (
        JobApplicationInterview.objects.filter(pk=interview_id, is_deleted=False)
        .select_related("application", "application__job_seeker")
        .first()
    )
    if not interview:
        return False
    if interview.status in {"cancelled", "completed"}:
        return False
    if interview.scheduled_at <= timezone.now():
        return False

    sent = interview.reminder_sent_at or {}
    if sent.get(reminder_type):
        return False

    try:
        ApplicationEventService().record_interview_reminder(
            interview.application, interview, reminder_type=reminder_type
        )
        sent[reminder_type] = timezone.now().isoformat()
        interview.reminder_sent_at = sent
        interview.save(update_fields=["reminder_sent_at", "updated_at"])
        return True
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    base=BaseTask,
    name="applications.scan_upcoming_interviews",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
@redis_lock("scan_upcoming_interviews")
def scan_upcoming_interviews_task(self) -> int:
    """Fallback scanner for interviews starting within 24 hours."""
    from datetime import timedelta

    from apps.applications.models import JobApplicationInterview

    now = timezone.now()
    window_end = now + timedelta(hours=24)
    count = 0
    interviews = JobApplicationInterview.objects.filter(
        is_deleted=False,
        scheduled_at__gt=now,
        scheduled_at__lte=window_end,
        status__in=["scheduled", "confirmed", "rescheduled"],
    )
    for interview in interviews:
        delta_minutes = int((interview.scheduled_at - now).total_seconds() // 60)
        if delta_minutes <= 15:
            reminder_type = "15m"
        elif delta_minutes <= 60:
            reminder_type = "1h"
        else:
            reminder_type = "24h"
        try:
            if send_interview_reminder_task.delay(str(interview.pk), reminder_type):
                count += 1
        except Exception as exc:
            raise self.retry(exc=exc)
    return count
