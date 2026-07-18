"""Recruiter messages portal — timeline activity and candidate communications."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus, TimelineEventType
from apps.applications.models import JobApplicationTimelineEvent
from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import initials_from_name
from apps.notifications.models import Notification


EVENT_LABELS = {
    TimelineEventType.CREATED: "New application",
    TimelineEventType.STATUS_CHANGED: "Status update",
    TimelineEventType.RECRUITER_COMMENT: "Your note",
    TimelineEventType.CANDIDATE_ACTION: "Candidate action",
    TimelineEventType.WITHDRAW: "Withdrawn",
    TimelineEventType.OFFER: "Offer update",
    TimelineEventType.HIRE: "Hired",
    TimelineEventType.REJECT: "Rejected",
}

STATUS_LABELS = dict(JobApplicationStatus.choices)


@dataclass
class RecruiterMessagesPortalContext:
    threads: list[dict]
    unread_count: int


class RecruiterMessagesPortalService(BaseService):
    MESSAGE_NOTIFICATION_TYPES = (
        "application.submitted",
        "application.status_changed",
        "resume.viewed",
        "resume_downloaded",
        "interview.scheduled",
        "candidate.message",
    )

    def build(self, profile: RecruiterProfile) -> RecruiterMessagesPortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )

        timeline_rows = (
            JobApplicationTimelineEvent.objects.filter(
                application__job_posting__company_id__in=company_ids,
                application__is_deleted=False,
            )
            .select_related("application")
            .order_by("-occurred_at")[:40]
        )

        threads: list[dict] = []
        for row in timeline_rows:
            app = row.application
            label = EVENT_LABELS.get(
                row.event_type, row.event_type.replace("_", " ").title()
            )
            body = row.notes.strip()
            if not body and row.to_status:
                body = f"Status changed to {STATUS_LABELS.get(row.to_status, row.to_status)}."
            if not body:
                body = f"{label} for {app.job_title_snapshot}."
            threads.append(
                {
                    "id": f"tl-{row.pk}",
                    "kind": "timeline",
                    "sort_at": row.occurred_at,
                    "title": app.applicant_name_snapshot,
                    "subtitle": app.job_title_snapshot,
                    "preview": body[:240],
                    "occurred_label": timezone.localtime(row.occurred_at).strftime(
                        "%b %d, %Y · %I:%M %p"
                    ),
                    "initials": initials_from_name(app.applicant_name_snapshot, "C"),
                    "badge": label,
                    "url": pu("recruiter_candidates"),
                    "is_unread": False,
                }
            )

        notifications = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=user.pk,
            is_deleted=False,
        ).order_by("-created_at")[:20]

        for note in notifications:
            threads.append(
                {
                    "id": f"nt-{note.pk}",
                    "kind": "notification",
                    "sort_at": note.created_at,
                    "title": note.title,
                    "subtitle": note.event_type.replace(".", " ")
                    .replace("_", " ")
                    .title(),
                    "preview": (note.body or "")[:240],
                    "occurred_label": timezone.localtime(note.created_at).strftime(
                        "%b %d, %Y · %I:%M %p"
                    ),
                    "initials": "N",
                    "badge": "Alert",
                    "url": pu("recruiter_notifications"),
                    "is_unread": not note.is_read,
                }
            )

        threads.sort(key=lambda t: t["sort_at"], reverse=True)
        for item in threads:
            item.pop("sort_at", None)
        unread = sum(1 for t in threads if t["is_unread"])

        return RecruiterMessagesPortalContext(threads=threads[:50], unread_count=unread)
