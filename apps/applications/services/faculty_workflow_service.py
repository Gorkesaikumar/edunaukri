from django.utils import timezone

from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication
from apps.applications.repositories.application_repository import (
    FacultyApplicationRepository,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.application_event_service import ApplicationEventService
from apps.applications.services.faculty_application_history_service import (
    FacultyApplicationHistoryService,
)
from apps.applications.services.faculty_application_validation_service import (
    FacultyApplicationValidationService,
)
from apps.applications.services.faculty_base import FacultyApplicationServiceBase
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.services.base import BaseService
from apps.invoices.services.placement_invoice_service import PlacementInvoiceService


class FacultyWorkflowService(FacultyApplicationServiceBase):
    """Status transitions for faculty applications via the centralized workflow engine."""

    def __init__(self):
        super().__init__()
        self.repository = FacultyApplicationRepository()
        self.validation = FacultyApplicationValidationService()
        self.history = FacultyApplicationHistoryService()
        self.authorization = ApplicationAuthorizationService()
        self.events = ApplicationEventService()

    @BaseService.atomic
    def update_status_for_actor(
        self,
        application: FacultyApplication,
        new_status: str,
        notes: str,
        *,
        actor,
        rejection_reason: str = "",
    ) -> FacultyApplication:
        normalized = self.validation.normalize_status(new_status)
        self.authorization.ensure_can_update_faculty_status(
            application, normalized, actor
        )
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
        application: FacultyApplication,
        new_status: str,
        notes: str = "",
        *,
        rejection_reason: str = "",
        actor=None,
    ) -> FacultyApplication:
        current = application.status
        self.validation.validate_transition(application, new_status)

        application.status = new_status
        application.status_changed_at = timezone.now()
        update_fields = ["status", "status_changed_at", "updated_at"]

        if new_status == FacultyApplicationStatus.JOINED:
            now = timezone.now()
            application.joined_at = now
            application.placed_at = now
            update_fields.extend(["joined_at", "placed_at"])
        if new_status == FacultyApplicationStatus.REJECTED:
            application.rejection_reason = rejection_reason or notes
            update_fields.append("rejection_reason")
        elif current == FacultyApplicationStatus.REJECTED:
            application.rejection_reason = ""
            update_fields.append("rejection_reason")

        application.save(update_fields=update_fields)
        self.history.record_status_change(
            application, from_status=current, to_status=new_status, notes=notes
        )
        self.events.record_faculty_status_changed(application, current, new_status)
        
        # Real-time WebSocket notifications
        from django.db import transaction
        from apps.notifications.services.application_status_notification_service import ApplicationStatusNotificationService
        transaction.on_commit(lambda: ApplicationStatusNotificationService().notify_status_change(
            application, "faculty", current, new_status
        ))

        if new_status == FacultyApplicationStatus.JOINED:
            self._publish_joined_event(application)

        actor_id = getattr(actor, "pk", None) if actor else None
        self._audit(
            application,
            "application.status_changed",
            actor_id,
            {"from_status": current, "to_status": new_status},
            actor=actor,
        )

        if new_status == FacultyApplicationStatus.JOINED:
            try:
                invoice_service = PlacementInvoiceService()
                invoice_service.generate_for_faculty_placement(application)
            except Exception as e:
                # Log error but don't fail the workflow transition
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to generate placement invoice for application {application.pk}: {e}")

        return application

    def _publish_joined_event(self, application: FacultyApplication) -> None:
        from apps.core.services.outbox_service import OutboxService

        vacancy = application.vacancy
        OutboxService().publish(
            domain=DomainType.FACULTY,
            event_type="application.joined",
            aggregate_type="faculty_application",
            aggregate_id=application.pk,
            payload={
                "recipient_domain": "professor",
                "recipient_id": str(application.professor.user_id),
                "title": "Welcome — you have joined",
                "body": f"You have joined {application.college_name_snapshot or application.vacancy_title_snapshot}.",
                "billing": {
                    "entity_type": EntityReferenceType.FACULTY_APPLICATION,
                    "entity_id": str(application.pk),
                    "entity_title": application.vacancy_title_snapshot,
                    "bill_to_entity_type": EntityReferenceType.FACULTY_COLLEGE,
                    "bill_to_entity_id": str(vacancy.college_id),
                    "bill_to_name": vacancy.college_name_snapshot,
                    "base_amount": str(
                        application.expected_salary
                        or vacancy.salary_max
                        or vacancy.salary_min
                        or 0
                    ),
                    "created_by_id": str(application.professor.user_id),
                },
            },
        )
