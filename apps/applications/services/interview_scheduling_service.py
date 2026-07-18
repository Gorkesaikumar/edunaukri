from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus, TimelineEventType
from apps.applications.constants.interview_enums import InterviewStatus
from apps.applications.models import JobApplication, JobApplicationInterview
from apps.applications.repositories.application_repository import (
    JobApplicationRepository,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.application_event_service import ApplicationEventService
from apps.applications.services.application_history_service import (
    ApplicationHistoryService,
)
from apps.applications.services.application_validation_service import (
    ApplicationValidationService,
)
from apps.applications.services.application_workflow_service import (
    ApplicationWorkflowService,
)
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService


class InterviewSelector:
    def for_application(self, application: JobApplication):
        return JobApplicationInterview.objects.filter(
            application=application, is_deleted=False
        )

    def for_seeker(self, profile):
        return JobApplicationInterview.objects.filter(
            application__job_seeker=profile,
            application__is_deleted=False,
            is_deleted=False,
        ).select_related(
            "application",
            "application__job_posting",
            "application__job_posting__company",
            "application__job_posting__posted_by",
        )

    def latest_for_application(
        self, application: JobApplication
    ) -> JobApplicationInterview | None:
        return self.for_application(application).order_by("-scheduled_at").first()

    def get_active(self, interview_id) -> JobApplicationInterview | None:
        return (
            JobApplicationInterview.objects.filter(pk=interview_id, is_deleted=False)
            .select_related(
                "application", "application__job_posting", "application__job_seeker"
            )
            .first()
        )


class InterviewSchedulingService(BaseService):
    """Schedule, update, and cancel interviews for IT job applications."""

    REMINDER_OFFSETS = {
        "24h": 24 * 60,
        "1h": 60,
        "15m": 15,
    }

    def __init__(self):
        self.selector = InterviewSelector()
        self.repository = JobApplicationRepository()
        self.validation = ApplicationValidationService()
        self.history = ApplicationHistoryService()
        self.workflow = ApplicationWorkflowService()
        self.authorization = ApplicationAuthorizationService()
        self.events = ApplicationEventService()

    @BaseService.atomic
    def schedule(
        self,
        application: JobApplication,
        *,
        actor,
        scheduled_at,
        round_type: str = "technical",
        round_label: str = "",
        interview_type: str = "Technical Interview",
        mode: str = "online",
        duration_minutes: int = 45,
        timezone_label: str = "IST",
        meet_url: str = "",
        location: str = "",
        panel=None,
        instructions: str = "",
        required_documents=None,
        notes: str = "",
        transition_status: bool = True,
    ) -> JobApplicationInterview:
        self.authorization.ensure_can_update_it_status(
            application, JobApplicationStatus.INTERVIEW_SCHEDULED, actor
        )
        from apps.it_recruitment.services.jobseeker_privacy_service import (
            JobSeekerPrivacyService,
        )

        JobSeekerPrivacyService().ensure_can_recruiter_contact(
            application.job_seeker, actor, application=application
        )
        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at)

        interview = JobApplicationInterview.objects.create(
            application=application,
            domain=DomainType.IT,
            interview_id=f"INT-{application.pk.hex[:8].upper()}",
            round_type=round_type,
            round_label=round_label,
            interview_type=interview_type,
            mode=mode,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            timezone_label=timezone_label,
            meet_url=meet_url,
            location=location,
            panel=panel or [],
            instructions=instructions,
            required_documents=required_documents or [],
            status=InterviewStatus.SCHEDULED,
            scheduled_by_id=getattr(actor, "pk", None),
            created_by_id=getattr(actor, "pk", None),
        )
        metadata = interview.to_metadata()
        note = (
            notes
            or f"Interview scheduled for {scheduled_at.strftime('%b %d, %Y at %I:%M %p')}."
        )

        if (
            transition_status
            and application.status != JobApplicationStatus.INTERVIEW_SCHEDULED
        ):
            self.validation.validate_transition(
                application, JobApplicationStatus.INTERVIEW_SCHEDULED
            )
            self.workflow.update_status(
                application,
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                note,
                actor=actor,
                timeline_metadata=metadata,
            )
        else:
            self.history.record_comment(
                application,
                notes=note,
                event_type=TimelineEventType.RECRUITER_COMMENT,
                actor_id=getattr(actor, "pk", None),
                metadata=metadata,
            )

        self.events.record_interview_scheduled(application, interview)
        self._schedule_reminders(interview)
        return interview

    @BaseService.atomic
    def update_interview(
        self,
        interview: JobApplicationInterview,
        *,
        actor,
        **fields,
    ) -> JobApplicationInterview:
        application = interview.application
        self.authorization.ensure_can_update_it_status(
            application, application.status, actor
        )

        allowed = {
            "scheduled_at",
            "round_type",
            "round_label",
            "interview_type",
            "mode",
            "duration_minutes",
            "timezone_label",
            "meet_url",
            "location",
            "panel",
            "instructions",
            "required_documents",
            "feedback",
            "feedback_shared",
            "status",
        }
        changed_meet = False
        changed_schedule = False
        for key, value in fields.items():
            if key not in allowed or value is None:
                continue
            if key == "scheduled_at" and timezone.is_naive(value):
                value = timezone.make_aware(value)
            if key == "meet_url" and value != interview.meet_url:
                changed_meet = True
            if key == "scheduled_at" and value != interview.scheduled_at:
                changed_schedule = True
            setattr(interview, key, value)

        if changed_schedule:
            interview.status = InterviewStatus.RESCHEDULED
        interview.updated_by_id = getattr(actor, "pk", None)
        interview.save()

        metadata = interview.to_metadata()
        note = "Interview details updated."
        if changed_schedule:
            note = "Interview rescheduled."
        elif changed_meet:
            note = "Meeting link updated."

        self.history.record_comment(
            application,
            notes=note,
            event_type=TimelineEventType.RECRUITER_COMMENT,
            actor_id=getattr(actor, "pk", None),
            metadata=metadata,
        )

        if changed_schedule:
            self.events.record_interview_rescheduled(application, interview)
            self._schedule_reminders(interview)
        elif changed_meet:
            self.events.record_meeting_link_updated(application, interview)
        elif fields.get("instructions"):
            self.events.record_interview_instructions_updated(application, interview)

        if fields.get("feedback_shared"):
            self.events.record_interview_feedback_available(application, interview)

        return interview

    @BaseService.atomic
    def cancel(
        self, interview: JobApplicationInterview, *, actor, reason: str = ""
    ) -> JobApplicationInterview:
        application = interview.application
        self.authorization.ensure_can_update_it_status(
            application, application.status, actor
        )
        interview.status = InterviewStatus.CANCELLED
        interview.save(update_fields=["status", "updated_at"])
        note = reason.strip() or "Interview cancelled."
        self.history.record_comment(
            application,
            notes=note,
            event_type=TimelineEventType.RECRUITER_COMMENT,
            actor_id=getattr(actor, "pk", None),
            metadata=interview.to_metadata(),
        )
        self.events.record_interview_cancelled(application, interview, reason=note)
        return interview

    @BaseService.atomic
    def confirm_by_candidate(
        self, interview: JobApplicationInterview, *, actor
    ) -> JobApplicationInterview:
        if interview.status == InterviewStatus.CANCELLED:
            raise ValueError("This interview was cancelled.")
        interview.mark_confirmed()
        self.history.record_comment(
            interview.application,
            notes="Candidate confirmed interview attendance.",
            event_type=TimelineEventType.CANDIDATE_ACTION,
            actor_id=getattr(actor, "pk", None),
            metadata=interview.to_metadata(),
        )
        self.events.record_interview_confirmed(interview.application, interview)
        return interview

    @BaseService.atomic
    def request_reschedule_by_candidate(
        self, interview: JobApplicationInterview, *, actor, reason: str = ""
    ) -> JobApplicationInterview:
        if interview.status in (InterviewStatus.CANCELLED, InterviewStatus.COMPLETED):
            raise ValueError("Reschedule is not available for this interview.")
        note = reason.strip() or "Candidate requested a reschedule."
        interview.status = InterviewStatus.RESCHEDULED
        interview.save(update_fields=["status", "updated_at"])
        self.history.record_comment(
            interview.application,
            notes=f"Reschedule requested: {note}",
            event_type=TimelineEventType.CANDIDATE_ACTION,
            actor_id=getattr(actor, "pk", None),
            metadata=interview.to_metadata(),
        )
        self.events.record_interview_reschedule_requested(
            interview.application, interview, reason=note
        )
        return interview

    def _schedule_reminders(self, interview: JobApplicationInterview) -> None:
        from apps.applications.tasks import send_interview_reminder_task

        for reminder_type in self.REMINDER_OFFSETS:
            minutes = self.REMINDER_OFFSETS[reminder_type]
            eta = interview.scheduled_at - timezone.timedelta(minutes=minutes)
            if eta <= timezone.now():
                continue
            send_interview_reminder_task.apply_async(
                args=[str(interview.pk), reminder_type],
                eta=eta,
            )
