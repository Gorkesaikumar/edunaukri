from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
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
from apps.applications.services.base import ApplicationServiceBase
from apps.applications.workflow.engine import ApplicationWorkflowEngine
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.services.base import BaseService


class ApplicationWorkflowService(ApplicationServiceBase):
    """Status transitions for job applications via the centralized workflow engine."""

    def __init__(self):
        super().__init__()
        self.repository = JobApplicationRepository()
        self.validation = ApplicationValidationService()
        self.history = ApplicationHistoryService()
        self.authorization = ApplicationAuthorizationService()
        self.events = ApplicationEventService()

    @BaseService.atomic
    def update_status_for_actor(
        self,
        application: JobApplication,
        new_status: str,
        notes: str,
        *,
        actor,
        rejection_reason: str = "",
    ) -> JobApplication:
        normalized = self.validation.normalize_status(new_status)
        self.authorization.ensure_can_update_it_status(application, normalized, actor)
        return self.update_status(
            application,
            normalized,
            notes,
            rejection_reason=rejection_reason,
            actor=actor,
        )

    @BaseService.atomic
    def update_status(
        self,
        application: JobApplication,
        new_status: str,
        notes: str = "",
        *,
        rejection_reason: str = "",
        actor=None,
        timeline_metadata: dict | None = None,
    ) -> JobApplication:
        current = application.status
        self.validation.validate_transition(application, new_status)

        application.status = new_status
        application.status_changed_at = timezone.now()
        update_fields = ["status", "status_changed_at", "updated_at"]

        if new_status == JobApplicationStatus.HIRED:
            now = timezone.now()
            application.hired_at = now
            application.placed_at = now
            update_fields.extend(["hired_at", "placed_at"])
        if new_status == JobApplicationStatus.REJECTED:
            application.rejection_reason = rejection_reason or notes
            update_fields.append("rejection_reason")
        elif current == JobApplicationStatus.REJECTED:
            application.rejection_reason = ""
            update_fields.append("rejection_reason")

        application.save(update_fields=update_fields)
        self.history.record_status_change(
            application,
            from_status=current,
            to_status=new_status,
            notes=notes,
            actor_id=getattr(actor, "pk", None) if actor else None,
            metadata=timeline_metadata,
        )
        self.events.record_it_status_changed(application, current, new_status)
        
        # Real-time WebSocket notifications
        from django.db import transaction
        from apps.notifications.services.application_status_notification_service import ApplicationStatusNotificationService
        transaction.on_commit(lambda: ApplicationStatusNotificationService().notify_status_change(
            application, "it", current, new_status
        ))

        if new_status == JobApplicationStatus.HIRED:
            self._publish_hired_event(application)

        actor_id = getattr(actor, "pk", None) if actor else None
        self._audit(
            application,
            "application.status_changed",
            actor_id,
            {"from_status": current, "to_status": new_status},
        )
        return application

    def _publish_hired_event(self, application: JobApplication) -> None:
        from apps.core.services.outbox_service import OutboxService

        job = application.job_posting
        OutboxService().publish(
            domain=DomainType.IT,
            event_type="application.hired",
            aggregate_type="it_job_application",
            aggregate_id=application.pk,
            payload={
                "recipient_domain": "it",
                "recipient_id": str(application.job_seeker.user_id),
                "title": "Congratulations — you have been hired",
                "body": f"You have been hired for {application.job_title_snapshot}.",
                "billing": {
                    "entity_type": EntityReferenceType.IT_JOB_APPLICATION,
                    "entity_id": str(application.pk),
                    "entity_title": application.job_title_snapshot,
                    "bill_to_entity_type": EntityReferenceType.IT_COMPANY,
                    "bill_to_entity_id": str(job.company_id),
                    "bill_to_name": job.company_name_snapshot,
                    "base_amount": str(
                        application.expected_salary
                        or application.job_seeker.expected_salary
                        or 0
                    ),
                    "created_by_id": str(application.job_seeker.user_id),
                },
            },
        )
