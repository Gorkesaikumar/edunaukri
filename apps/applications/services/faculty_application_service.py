from django.utils import timezone

from apps.applications.constants.faculty_enums import (
    FacultyApplicationStatus,
    FacultyTimelineEventType,
)
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
from apps.applications.services.faculty_workflow_service import FacultyWorkflowService
from apps.applications.workflow.faculty_engine import FacultyApplicationWorkflowEngine
from apps.core.services.base import BaseService
from apps.faculty.models import FacultyVacancy
from apps.faculty.repositories.vacancy_repository import FacultyVacancyRepository
from apps.academic_recruitment.services.faculty_application_eligibility_service import FacultyApplicationEligibilityService


class FacultyApplicationService(FacultyApplicationServiceBase):
    """Create, withdraw, notes, and delegate status changes for faculty applications."""

    def __init__(self):
        super().__init__()
        self.repository = FacultyApplicationRepository()
        self.vacancy_repository = FacultyVacancyRepository()
        self.validation = FacultyApplicationValidationService()
        self.history = FacultyApplicationHistoryService()
        self.workflow = FacultyWorkflowService()
        self.authorization = ApplicationAuthorizationService()
        self.events = ApplicationEventService()

    @BaseService.atomic
    def apply(
        self,
        *,
        vacancy: FacultyVacancy,
        professor,
        cover_letter="",
        cv_file=None,
        expected_salary=None,
        current_institution="",
        current_designation="",
        source="",
    ) -> FacultyApplication:
        from apps.core.exceptions.domain_exceptions import ValidationException
        
        eligibility = FacultyApplicationEligibilityService().check(professor, vacancy)
        if not eligibility.eligible:
            if "already applied" in eligibility.message:
                from apps.core.exceptions.domain_exceptions import ConflictException
                raise ConflictException(eligibility.message)
            raise ValidationException(eligibility.message)


        from apps.core.services.config import get_setting
        from apps.core.exceptions.domain_exceptions import ValidationException

        max_apps = get_setting("limits.max_applications_per_job", {"count": 500}).get(
            "count", 500
        )
        current_apps = vacancy.applications.filter(is_deleted=False).count()
        if current_apps >= max_apps:
            raise ValidationException("Application limit has been reached.")

        self.validation.validate_apply_payload(
            {"expected_salary": expected_salary, "source": source or "direct"}
        )

        cv = cv_file or professor.cv_file
        self.validation.validate_cv_presence(cv)
        application = self.repository.create(
            vacancy=vacancy,
            professor=professor,
            college=vacancy.college,
            cv_file=cv,
            cv_snapshot=self._build_cv_snapshot(cv),
            qualification_snapshot=self._build_qualification_snapshot(professor),
            specialization_snapshot=self._build_specialization_snapshot(professor),
            experience_snapshot=self._build_experience_snapshot(professor),
            certificates_snapshot=self._build_certificates_snapshot(professor),
            cover_letter=cover_letter,
            department=vacancy.department or "",
            expected_salary=expected_salary or professor.expected_salary,
            current_institution=current_institution or professor.current_institution,
            current_designation=current_designation or professor.current_designation,
            research_publications_count=professor.publications_count or 0,
            source=source or "direct",
            status=FacultyApplicationWorkflowEngine.initial_status(),
            applicant_name_snapshot=professor.full_name,
            vacancy_title_snapshot=vacancy.title,
            college_name_snapshot=vacancy.college_name_snapshot,
            created_by_id=professor.user_id,
        )
        self.vacancy_repository.increment_application_count(vacancy)
        self.history.record_status_change(
            application,
            from_status=None,
            to_status=application.status,
            notes="Application submitted.",
            actor_id=professor.user_id,
        )
        self.events.record_faculty_applied(application)
        self._audit(
            application,
            "application.created",
            professor.user_id,
            {"vacancy_id": str(vacancy.pk)},
            actor=professor.user,
        )

        from apps.notifications.models import Notification
        from apps.notifications.constants.enums import NotificationChannel
        from apps.colleges.models.college import CollegeMember

        recruiter_ids = CollegeMember.objects.filter(
            college=vacancy.college, is_deleted=False
        ).values_list("college_user_id", flat=True)

        notifications = [
            Notification(
                recipient_domain="college",
                recipient_id=recruiter_id,
                channel=NotificationChannel.IN_APP,
                title="New Application Received",
                body=f"{professor.full_name} applied for {vacancy.title}",
                event_type="NEW_FACULTY_APPLICATION",
                entity_type="FacultyApplication",
                entity_id=application.pk,
                payload={
                    "application_id": str(application.pk),
                    "candidate_name": professor.full_name,
                    "vacancy_name": vacancy.title,
                    "institution": vacancy.college.name,
                }
            )
            for recruiter_id in set(recruiter_ids)
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)

        return application

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
        return self.workflow.update_status_for_actor(
            application,
            new_status,
            notes,
            actor=actor,
            rejection_reason=rejection_reason,
        )

    @BaseService.atomic
    def withdraw(self, application: FacultyApplication, *, actor) -> FacultyApplication:
        return self.workflow.update_status_for_actor(
            application,
            FacultyApplicationStatus.WITHDRAWN,
            notes="Withdrawn by applicant.",
            actor=actor,
        )

    @BaseService.atomic
    def add_college_notes(
        self, application: FacultyApplication, *, notes: str, actor
    ) -> FacultyApplication:
        self.authorization.ensure_can_update_faculty_status(
            application, application.status, actor
        )
        application.college_notes = notes
        application.save(update_fields=["college_notes", "updated_at"])
        self.history.record_comment(
            application,
            notes=notes,
            event_type=FacultyTimelineEventType.COLLEGE_COMMENT,
            actor_id=getattr(actor, "pk", None),
        )
        return application

    @BaseService.atomic
    def add_internal_remarks(
        self, application: FacultyApplication, *, remarks: str, actor
    ) -> FacultyApplication:
        self.authorization.ensure_can_update_faculty_status(
            application, application.status, actor
        )
        application.internal_remarks = remarks
        application.save(update_fields=["internal_remarks", "updated_at"])
        self.history.record_comment(
            application,
            notes=remarks,
            event_type=FacultyTimelineEventType.COLLEGE_COMMENT,
            actor_id=getattr(actor, "pk", None),
        )
        return application

    @BaseService.atomic
    def add_college_rating(
        self, application: FacultyApplication, *, rating: int | None, actor
    ) -> FacultyApplication:
        self.authorization.ensure_can_update_faculty_status(
            application, application.status, actor
        )
        if rating is not None and (rating < 1 or rating > 5):
            raise ValueError("Rating must be between 1 and 5.")
        application.college_rating = rating
        application.save(update_fields=["college_rating", "updated_at"])
        self.history.record_comment(
            application,
            notes=f"College rating set to {rating}/5."
            if rating
            else "College rating cleared.",
            event_type=FacultyTimelineEventType.COLLEGE_COMMENT,
            actor_id=getattr(actor, "pk", None),
        )
        return application

    @BaseService.atomic
    def add_professor_notes(
        self, application: FacultyApplication, *, notes: str, actor
    ) -> FacultyApplication:
        self.authorization.ensure_can_update_professor_notes(application, actor)
        application.professor_notes = notes
        application.save(update_fields=["professor_notes", "updated_at"])
        self.history.record_comment(
            application,
            notes=notes,
            event_type=FacultyTimelineEventType.PROFESSOR_ACTION,
            actor_id=getattr(actor, "pk", None),
        )
        return application

    @BaseService.atomic
    def soft_delete(self, application: FacultyApplication, *, actor) -> None:
        self.authorization.ensure_can_soft_delete_faculty_application(
            application, actor
        )
        application.deleted_by_id = getattr(actor, "pk", None)
        application.save(update_fields=["deleted_by_id"])
        self.repository.soft_delete(application)

    @staticmethod
    def _build_cv_snapshot(cv_file) -> dict:
        if not cv_file:
            return {}
        return {
            "file_id": str(cv_file.pk),
            "original_filename": cv_file.original_filename,
            "mime_type": cv_file.mime_type,
            "file_size_bytes": cv_file.file_size_bytes,
            "captured_at": timezone.now().isoformat(),
        }

    @staticmethod
    def _build_qualification_snapshot(professor) -> list:
        return [
            {
                "qualification": q.qualification.name,
                "institution": q.institution_name,
                "year": q.year_obtained,
            }
            for q in professor.qualifications.select_related("qualification").all()
        ]

    @staticmethod
    def _build_specialization_snapshot(professor) -> dict:
        return {
            "specialization": professor.specialization,
            "research_interests": professor.research_interests,
            "highest_qualification": professor.highest_qualification,
        }

    @staticmethod
    def _build_experience_snapshot(professor) -> dict:
        return {
            "experience_years": professor.experience_years,
            "teaching_experience_years": professor.teaching_experience_years,
            "industry_experience_years": professor.industry_experience_years,
            "current_designation": professor.current_designation,
            "current_institution": professor.current_institution,
        }

    @staticmethod
    def _build_certificates_snapshot(professor) -> list:
        return [
            {
                "qualification": q.qualification.name,
                "file_id": str(q.certificate_file_id)
                if q.certificate_file_id
                else None,
                "original_filename": q.certificate_file.original_filename
                if q.certificate_file
                else "",
            }
            for q in professor.qualifications.select_related(
                "qualification", "certificate_file"
            ).all()
        ]
