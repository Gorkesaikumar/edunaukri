from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication, JobApplication
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService


class ApplicationEventService(BaseService):
    """Publishes outbox notifications and audit records for application lifecycle events."""

    def __init__(self):
        self.outbox = OutboxService()

    def record_it_applied(self, application: JobApplication) -> None:
        self._audit(
            domain=DomainType.IT,
            event_type="application.submitted",
            entity_type=EntityReferenceType.IT_JOB_APPLICATION,
            entity_id=application.pk,
            payload={
                "job_posting_id": str(application.job_posting_id),
                "job_seeker_id": str(application.job_seeker_id),
                "status": application.status,
            },
        )
        job = application.job_posting
        if job.posted_by_id:
            self._publish(
                domain=DomainType.IT,
                event_type="application.submitted",
                aggregate_type="it_job_application",
                aggregate_id=application.pk,
                recipient_domain="it",
                recipient_id=str(job.posted_by.user_id),
                title="New job application",
                body=f"{application.applicant_name_snapshot} applied for {application.job_title_snapshot}.",
            )

    def record_it_status_changed(
        self, application: JobApplication, from_status: str | None, to_status: str
    ) -> None:
        self._audit(
            domain=DomainType.IT,
            event_type="application.status_changed",
            entity_type=EntityReferenceType.IT_JOB_APPLICATION,
            entity_id=application.pk,
            payload={
                "from_status": from_status,
                "to_status": to_status,
                "job_posting_id": str(application.job_posting_id),
            },
        )
        if to_status == JobApplicationStatus.HIRED:
            return

        applicant_body = (
            f"Your application for {application.job_title_snapshot} is now "
            f"{to_status.replace('_', ' ')}."
        )
        if to_status == JobApplicationStatus.REJECTED and application.rejection_reason:
            applicant_body = f"{applicant_body} Reason: {application.rejection_reason}"

        self._publish(
            domain=DomainType.IT,
            event_type="application.status_changed",
            aggregate_type="it_job_application",
            aggregate_id=application.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Application status updated",
            body=applicant_body,
        )

        if to_status == JobApplicationStatus.WITHDRAWN:
            job = application.job_posting
            if job.posted_by_id:
                self._publish(
                    domain=DomainType.IT,
                    event_type="application.status_changed",
                    aggregate_type="it_job_application",
                    aggregate_id=application.pk,
                    recipient_domain="it",
                    recipient_id=str(job.posted_by.user_id),
                    title="Application withdrawn",
                    body=f"{application.applicant_name_snapshot} withdrew their application for {application.job_title_snapshot}.",
                )

    def record_faculty_applied(self, application: FacultyApplication) -> None:
        self._audit(
            domain=DomainType.FACULTY,
            event_type="application.submitted",
            entity_type=EntityReferenceType.FACULTY_APPLICATION,
            entity_id=application.pk,
            payload={
                "vacancy_id": str(application.vacancy_id),
                "professor_id": str(application.professor_id),
                "status": application.status,
            },
        )
        vacancy = application.vacancy
        if vacancy.posted_by_id:
            self._publish(
                domain=DomainType.FACULTY,
                event_type="application.submitted",
                aggregate_type="faculty_application",
                aggregate_id=application.pk,
                recipient_domain="college",
                recipient_id=str(vacancy.posted_by_id),
                title="New faculty application",
                body=f"{application.applicant_name_snapshot} applied for {application.vacancy_title_snapshot}.",
            )

    def record_faculty_status_changed(
        self, application: FacultyApplication, from_status: str | None, to_status: str
    ) -> None:
        self._audit(
            domain=DomainType.FACULTY,
            event_type="application.status_changed",
            entity_type=EntityReferenceType.FACULTY_APPLICATION,
            entity_id=application.pk,
            payload={
                "from_status": from_status,
                "to_status": to_status,
                "vacancy_id": str(application.vacancy_id),
            },
        )
        if to_status == FacultyApplicationStatus.JOINED:
            return

        applicant_body = (
            f"Your application for {application.vacancy_title_snapshot} is now "
            f"{to_status.replace('_', ' ')}."
        )
        if (
            to_status == FacultyApplicationStatus.REJECTED
            and application.rejection_reason
        ):
            applicant_body = f"{applicant_body} Reason: {application.rejection_reason}"

        self._publish(
            domain=DomainType.FACULTY,
            event_type="application.status_changed",
            aggregate_type="faculty_application",
            aggregate_id=application.pk,
            recipient_domain="professor",
            recipient_id=str(application.professor.user_id),
            title="Application status updated",
            body=applicant_body,
        )

        if to_status == FacultyApplicationStatus.WITHDRAWN:
            vacancy = application.vacancy
            if vacancy.posted_by_id:
                self._publish(
                    domain=DomainType.FACULTY,
                    event_type="application.status_changed",
                    aggregate_type="faculty_application",
                    aggregate_id=application.pk,
                    recipient_domain="college",
                    recipient_id=str(vacancy.posted_by_id),
                    title="Application withdrawn",
                    body=(
                        f"{application.applicant_name_snapshot} withdrew their application "
                        f"for {application.vacancy_title_snapshot}."
                    ),
                )

    def record_interview_scheduled(
        self, application: JobApplication, interview
    ) -> None:
        when = interview.scheduled_at.strftime("%b %d, %Y at %I:%M %p")
        self._publish(
            domain=DomainType.IT,
            event_type="interview.scheduled",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Interview scheduled",
            body=(
                f"{interview.round_label or interview.interview_type} for "
                f"{application.job_title_snapshot} is scheduled on {when} ({interview.timezone_label})."
            ),
        )
        self._deliver_pending()

    def record_interview_rescheduled(
        self, application: JobApplication, interview
    ) -> None:
        when = interview.scheduled_at.strftime("%b %d, %Y at %I:%M %p")
        self._publish(
            domain=DomainType.IT,
            event_type="interview.rescheduled",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Interview rescheduled",
            body=f"Your interview has been moved to {when} ({interview.timezone_label}).",
        )
        self._deliver_pending()

    def record_meeting_link_updated(
        self, application: JobApplication, interview
    ) -> None:
        self._publish(
            domain=DomainType.IT,
            event_type="interview.meeting_link_updated",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Meeting link updated",
            body=f"The meeting link for your {application.job_title_snapshot} interview was updated.",
        )
        self._deliver_pending()

    def record_interview_instructions_updated(
        self, application: JobApplication, interview
    ) -> None:
        self._publish(
            domain=DomainType.IT,
            event_type="interview.instructions_updated",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Interview instructions updated",
            body=f"New instructions were shared for your {application.job_title_snapshot} interview.",
        )
        self._deliver_pending()

    def record_interview_cancelled(
        self, application: JobApplication, interview, *, reason: str = ""
    ) -> None:
        body = (
            reason
            or f"Your interview for {application.job_title_snapshot} was cancelled."
        )
        self._publish(
            domain=DomainType.IT,
            event_type="interview.cancelled",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Interview cancelled",
            body=body,
        )
        self._deliver_pending()

    def record_interview_confirmed(
        self, application: JobApplication, interview
    ) -> None:
        job = application.job_posting
        if not job.posted_by_id:
            return
        self._publish(
            domain=DomainType.IT,
            event_type="interview.confirmed",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(job.posted_by.user_id),
            title="Candidate confirmed interview",
            body=f"{application.applicant_name_snapshot} confirmed attendance for {application.job_title_snapshot}.",
        )
        self._deliver_pending()

    def record_interview_reschedule_requested(
        self, application: JobApplication, interview, *, reason: str = ""
    ) -> None:
        job = application.job_posting
        if not job.posted_by_id:
            return
        body = (
            reason or f"{application.applicant_name_snapshot} requested a reschedule."
        )
        self._publish(
            domain=DomainType.IT,
            event_type="interview.reschedule_requested",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(job.posted_by.user_id),
            title="Reschedule requested",
            body=body,
        )
        self._deliver_pending()

    def record_interview_feedback_available(
        self, application: JobApplication, interview
    ) -> None:
        self._publish(
            domain=DomainType.IT,
            event_type="interview.feedback_available",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title="Interview feedback available",
            body=f"Feedback is now available for your {application.job_title_snapshot} interview.",
        )
        self._deliver_pending()

    def record_interview_reminder(
        self, application: JobApplication, interview, *, reminder_type: str
    ) -> None:
        labels = {"24h": "24 hours", "1h": "1 hour", "15m": "15 minutes"}
        label = labels.get(reminder_type, reminder_type)
        when = interview.scheduled_at.strftime("%I:%M %p")
        self._publish(
            domain=DomainType.IT,
            event_type="interview.reminder",
            aggregate_type="it_job_application_interview",
            aggregate_id=interview.pk,
            recipient_domain="it",
            recipient_id=str(application.job_seeker.user_id),
            title=f"Interview reminder — {label}",
            body=(
                f"Your {interview.round_label or interview.interview_type} for "
                f"{application.job_title_snapshot} starts in {label} ({when} {interview.timezone_label})."
            ),
        )
        self._deliver_pending()

    def _deliver_pending(self) -> None:
        try:
            from apps.notifications.services.outbox_processor import (
                OutboxProcessorService,
            )

            OutboxProcessorService().process_batch(limit=10)
        except Exception:
            pass

    def _publish(
        self,
        *,
        domain: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id,
        recipient_domain: str,
        recipient_id: str,
        title: str,
        body: str,
    ) -> None:
        self.outbox.publish(
            domain=domain,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload={
                "recipient_domain": recipient_domain,
                "recipient_id": recipient_id,
                "title": title,
                "body": body,
            },
        )

    def _audit(self, *, domain, event_type, entity_type, entity_id, payload) -> None:
        from apps.audit.services.audit_service import AuditService

        AuditService().record(
            domain=domain,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
