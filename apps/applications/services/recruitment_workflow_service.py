import uuid
from decimal import Decimal
from datetime import timedelta, date, datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.applications.models import FacultyApplication, JobApplication, PlacementDetails
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.services.faculty_workflow_service import FacultyWorkflowService
from apps.applications.services.application_workflow_service import ApplicationWorkflowService
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.services.base import BaseService
from apps.invoices.services.placement_invoice_service import PlacementInvoiceService
from apps.invoices.models import Invoice
from apps.guarantee_claims.services.guarantee_service import GuaranteeService
from apps.guarantee_claims.models import PlacementGuarantee
from apps.guarantee_claims.constants.enums import GuaranteeStatus


class RecruitmentWorkflowService(BaseService):
    """Centralized Recruitment Workflow Service to manage candidate lifecycle and placement billing."""

    def __init__(self):
        self.faculty_workflow = FacultyWorkflowService()
        self.it_workflow = ApplicationWorkflowService()
        self.placement_invoice = PlacementInvoiceService()
        self.guarantee_service = GuaranteeService()

    def get_application(self, domain: str, application_id: uuid.UUID):
        if domain == "faculty" or domain == DomainType.FACULTY:
            return FacultyApplication.objects.get(pk=application_id)
        else:
            return JobApplication.objects.get(pk=application_id)

    @transaction.atomic
    def select_candidate(self, domain: str, application_id: uuid.UUID, actor, notes: str = "") -> PlacementDetails:
        """Transitions application status to SELECTED and initiates billing."""
        application = self.get_application(domain, application_id)
        
        # 1. Transition application status using existing workflow service
        if domain == "faculty" or domain == DomainType.FACULTY:
            self.faculty_workflow.update_status_for_actor(
                application,
                FacultyApplicationStatus.SELECTED,
                notes or "Candidate selected.",
                actor=actor,
            )
        else:
            self.it_workflow.update_status_for_actor(
                application,
                JobApplicationStatus.SELECTED,
                notes or "Candidate selected.",
                actor=actor,
            )

        # 2. Create or update PlacementDetails
        placement, _ = PlacementDetails.objects.get_or_create(
            domain=DomainType.FACULTY if domain == "faculty" or domain == DomainType.FACULTY else DomainType.IT,
            application_id=application_id,
            defaults={"selected_by_id": actor.pk}
        )
        placement.selected_at = timezone.now()
        placement.selected_by_id = actor.pk
        placement.save()

        # 3. Automatically generate invoice only for non-faculty domain
        if domain != "faculty" and domain != DomainType.FACULTY:
            self.placement_invoice.generate_for_selection(application)

        return placement

    @transaction.atomic
    def update_joining_details(self, domain: str, application_id: uuid.UUID, actor, data: dict) -> PlacementDetails:
        """Updates joining progression details and transitions to JOINING_IN_PROGRESS."""
        application = self.get_application(domain, application_id)

        # 1. Update status to JOINING_IN_PROGRESS if currently SELECTED
        if application.status == "selected":
            if domain == "faculty" or domain == DomainType.FACULTY:
                self.faculty_workflow.update_status_for_actor(
                    application,
                    FacultyApplicationStatus.JOINING_IN_PROGRESS,
                    "Joining progress initiated.",
                    actor=actor,
                )
            else:
                self.it_workflow.update_status_for_actor(
                    application,
                    JobApplicationStatus.JOINING_IN_PROGRESS,
                    "Joining progress initiated.",
                    actor=actor,
                )

        # 2. Save progress details
        placement, _ = PlacementDetails.objects.get_or_create(
            domain=DomainType.FACULTY if domain == "faculty" or domain == DomainType.FACULTY else DomainType.IT,
            application_id=application_id,
            defaults={"selected_by_id": actor.pk}
        )
        
        placement.expected_joining_date = data.get("expected_joining_date")
        placement.offered_designation = data.get("offered_designation", "")
        placement.department = data.get("department", "")
        placement.work_location = data.get("work_location", "")
        placement.employment_type = data.get("employment_type", "")
        
        salary = data.get("agreed_salary")
        if salary:
            placement.agreed_salary = Decimal(str(salary))
        
        placement.offer_reference_number = data.get("offer_reference_number", "")
        placement.joining_notes = data.get("joining_notes", "")
        placement.save()

        # Re-generate or update the invoice with the correct CTC/agreed salary
        if domain != "faculty" and domain != DomainType.FACULTY:
            self.placement_invoice.generate_for_selection(application)

        return placement

    @transaction.atomic
    def confirm_joined(self, domain: str, application_id: uuid.UUID, actor, data: dict) -> PlacementDetails:
        """Confirms candidate has joined, sets status to JOINED, and starts 90-day guarantee."""
        application = self.get_application(domain, application_id)

        # 1. Validate status transition
        if domain == "faculty" or domain == DomainType.FACULTY:
            self.faculty_workflow.update_status_for_actor(
                application,
                FacultyApplicationStatus.JOINED,
                data.get("notes", "Candidate joined confirmed."),
                actor=actor,
            )
        else:
            self.it_workflow.update_status_for_actor(
                application,
                JobApplicationStatus.JOINED,
                data.get("notes", "Candidate joined confirmed."),
                actor=actor,
            )

        # 2. Update actual joining details in PlacementDetails
        placement, _ = PlacementDetails.objects.get_or_create(
            domain=DomainType.FACULTY if domain == "faculty" or domain == DomainType.FACULTY else DomainType.IT,
            application_id=application_id,
            defaults={"selected_by_id": actor.pk}
        )
        
        actual_date = data.get("actual_joining_date")
        if isinstance(actual_date, str):
            actual_date = datetime.strptime(actual_date, "%Y-%m-%d").date()
        elif not actual_date:
            actual_date = timezone.now().date()

        placement.actual_joining_date = actual_date
        placement.employee_id = data.get("employee_id", "")
        placement.joining_confirmed_notes = data.get("notes", "")
        placement.joined_at = timezone.now()
        placement.joined_by_id = actor.pk
        placement.save()

        # 3. Generate invoice ONLY at actual joining for Faculty, or fetch existing for IT
        if domain == "faculty" or domain == DomainType.FACULTY:
            invoice = self.placement_invoice.generate_for_faculty_placement(application)
        else:
            from apps.billing.models.fee import PlacementFee
            fee = PlacementFee.objects.filter(entity_id=application_id, is_deleted=False).first()
            invoice = Invoice.objects.filter(placement_fee_id=fee.pk, is_deleted=False).first() if fee else None

        # 4. Create or start the 90-day Guarantee engine
        if invoice:
            # Create guarantee starting at actual joining date
            guarantee = self.guarantee_service.ensure_for_invoice(
                invoice=invoice,
                application_entity_type=EntityReferenceType.FACULTY_APPLICATION if domain == "faculty" or domain == DomainType.FACULTY else EntityReferenceType.IT_JOB_APPLICATION,
                application_entity_id=application_id,
                domain=DomainType.FACULTY if domain == "faculty" or domain == DomainType.FACULTY else DomainType.IT,
                guarantee_days=90
            )
            if guarantee:
                # Align guarantee start and expiration to actual joining date
                start_dt = timezone.make_aware(datetime.combine(actual_date, datetime.min.time()))
                guarantee.starts_at = start_dt
                guarantee.expires_at = start_dt + timedelta(days=90)
                guarantee.status = GuaranteeStatus.ACTIVE
                guarantee.save(update_fields=["starts_at", "expires_at", "status"])

        return placement

    @transaction.atomic
    def report_exit(self, domain: str, application_id: uuid.UUID, actor, data: dict) -> PlacementDetails:
        """Reports candidate exit/abscond and handles guarantee claim eligibility."""
        application = self.get_application(domain, application_id)
        
        target_status = FacultyApplicationStatus.REJECTED if domain == "faculty" or domain == DomainType.FACULTY else JobApplicationStatus.REJECTED
        notes = f"Exit reported: {data.get('reason', 'No reason provided')} ({data.get('exit_type', 'Other')})"

        # 1. Update application status
        if domain == "faculty" or domain == DomainType.FACULTY:
            self.faculty_workflow.update_status_for_actor(
                application, target_status, notes, actor=actor
            )
        else:
            self.it_workflow.update_status_for_actor(
                application, target_status, notes, actor=actor
            )

        # 2. Update guarantee status if applicable
        placement = PlacementDetails.objects.filter(
            domain=DomainType.FACULTY if domain == "faculty" or domain == DomainType.FACULTY else DomainType.IT,
            application_id=application_id
        ).first()

        exit_date_str = data.get("exit_date")
        if exit_date_str:
            if isinstance(exit_date_str, str):
                exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d").date()
            else:
                exit_date = exit_date_str
            
            # Find active guarantee
            guarantee = PlacementGuarantee.objects.filter(
                application_entity_id=application_id,
                status=GuaranteeStatus.ACTIVE,
                is_deleted=False
            ).first()

            if guarantee:
                exit_dt = timezone.make_aware(datetime.combine(exit_date, datetime.min.time()))
                if exit_dt <= guarantee.expires_at:
                    guarantee.status = GuaranteeStatus.CLAIM_ELIGIBLE
                else:
                    guarantee.status = GuaranteeStatus.EXPIRED
                guarantee.save(update_fields=["status"])

        return placement

    @transaction.atomic
    def complete_interview_with_evaluation(self, domain: str, application_id: uuid.UUID, actor, data: dict) -> InterviewEvaluation:
        """Saves interview evaluation ratings and moves the application to INTERVIEW_COMPLETED (or REJECTED)."""
        application = self.get_application(domain, application_id)
        
        # 1. Save evaluation ratings
        from apps.applications.models import InterviewEvaluation
        evaluation, _ = InterviewEvaluation.objects.get_or_create(
            domain=DomainType.FACULTY if domain == "faculty" or domain == DomainType.FACULTY else DomainType.IT,
            application_id=application_id,
            defaults={"created_by_id": actor.pk}
        )
        
        evaluation.technical_rating = int(data.get("technical_rating", 3))
        evaluation.communication_rating = int(data.get("communication_rating", 3))
        evaluation.subject_knowledge = int(data.get("subject_knowledge", 3))
        evaluation.teaching_skills = int(data.get("teaching_skills")) if data.get("teaching_skills") else None
        evaluation.industry_skills = int(data.get("industry_skills")) if data.get("industry_skills") else None
        evaluation.culture_fit = int(data.get("culture_fit", 3))
        evaluation.overall_rating = int(data.get("overall_rating", 3))
        evaluation.interview_notes = data.get("interview_notes", "")
        
        recommendation = data.get("recommendation", "hold").lower()
        evaluation.recommendation = recommendation
        evaluation.save()

        # 2. Transition status based on recommendation
        if recommendation == "reject":
            target_status = FacultyApplicationStatus.REJECTED if domain == "faculty" or domain == DomainType.FACULTY else JobApplicationStatus.REJECTED
            notes = "Rejected after interview: " + evaluation.interview_notes
        else:
            target_status = FacultyApplicationStatus.INTERVIEW_COMPLETED if domain == "faculty" or domain == DomainType.FACULTY else JobApplicationStatus.INTERVIEW_COMPLETED
            notes = f"Interview completed. Recommendation: {recommendation.upper()}."

        if domain == "faculty" or domain == DomainType.FACULTY:
            self.faculty_workflow.update_status_for_actor(
                application,
                target_status,
                notes,
                actor=actor,
            )
        else:
            self.it_workflow.update_status_for_actor(
                application,
                target_status,
                notes,
                actor=actor,
            )

        return evaluation

