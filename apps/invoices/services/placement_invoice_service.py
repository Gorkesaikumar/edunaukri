from decimal import Decimal
from django.db import transaction

from apps.applications.models import FacultyApplication, JobApplication, PlacementDetails
from apps.billing.services.placement_fee_service import PlacementFeeService
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.services.base import BaseService
from apps.invoices.models import Invoice
from apps.invoices.services.invoice_service import InvoiceGenerationService


class PlacementInvoiceService(BaseService):
    """Service to handle the creation of placement invoices upon candidate selection."""

    def __init__(self):
        self.fee_service = PlacementFeeService()
        self.invoice_generation_service = InvoiceGenerationService()

    @transaction.atomic
    def generate_for_selection(self, application) -> Invoice | None:
        """
        Generates a placement fee and invoice for a selected candidate (Faculty or IT).
        """
        # 1. Fetch placement details to get agreed salary
        placement_details = PlacementDetails.objects.filter(
            application_id=application.pk,
            is_deleted=False
        ).first()

        if not placement_details or not placement_details.agreed_salary:
            from django.core.exceptions import ValidationError
            raise ValidationError("Invoice cannot be generated because the candidate's final Annual CTC is missing.")
            
        annual_ctc = placement_details.agreed_salary
        
        # 2. Setup domain-specific values
        if isinstance(application, FacultyApplication):
            vacancy = application.vacancy
            domain = DomainType.FACULTY
            entity_type = EntityReferenceType.FACULTY_APPLICATION
            entity_title = application.vacancy_title_snapshot or vacancy.title
            bill_to_entity_type = EntityReferenceType.FACULTY_COLLEGE
            bill_to_entity_id = vacancy.college_id
            bill_to_name = vacancy.college_name_snapshot or vacancy.college.name
            created_by_id = application.professor.user_id
            
            candidate_name = f"{application.first_name} {application.last_name}"
            candidate_job = entity_title
            
        elif isinstance(application, JobApplication):
            job = application.job_posting
            domain = DomainType.IT
            entity_type = EntityReferenceType.IT_JOB_APPLICATION
            entity_title = application.job_title_snapshot or job.title
            bill_to_entity_type = EntityReferenceType.IT_COMPANY
            bill_to_entity_id = job.company_id
            bill_to_name = application.company_name_snapshot or job.company.name
            created_by_id = application.job_seeker.user_id
            
            candidate_name = f"{application.first_name} {application.last_name}"
            candidate_job = entity_title
        else:
            return None
            
        # 3. Calculate using new centralized Billing Calculator
        from apps.invoices.services.recruitment_billing_calculator import RecruitmentBillingCalculator
        calculator = RecruitmentBillingCalculator()
        calc_result = calculator.calculate(annual_ctc)

        # Ensure no duplicate invoices for this placement
        existing_invoice = Invoice.objects.filter(
            domain=domain,
            bill_to_entity_id=bill_to_entity_id,
            placement_fee_id=application.pk, # We can use application.pk here for tracking if no placement fee
            is_deleted=False
        ).first()
        
        if existing_invoice:
            return existing_invoice

        # 4. Generate invoice
        from apps.invoices.repositories.invoice_repository import InvoiceRepository, InvoiceLineItemRepository
        from django.utils import timezone
        import uuid
        
        prefix = timezone.now().strftime("INV-%Y%m")
        suffix = uuid.uuid4().hex[:8].upper()
        invoice_num = f"{prefix}-{suffix}"
        
        invoice = InvoiceRepository().create(
            invoice_number=invoice_num,
            domain=domain,
            placement_fee_id=application.pk, # Using application PK as reference
            bill_to_entity_type=bill_to_entity_type,
            bill_to_entity_id=bill_to_entity_id,
            bill_to_name_snapshot=bill_to_name,
            subtotal=calc_result.taxable_amount,
            tax_amount=calc_result.total_tax_amount,
            total_amount=calc_result.grand_total,
            currency=calc_result.currency,
            created_by_id=created_by_id,
        )
        
        # Save snapshots
        invoice.candidate_annual_ctc = calc_result.candidate_annual_ctc
        invoice.candidate_name = candidate_name
        invoice.candidate_job_title = candidate_job
        invoice.pricing_method_snapshot = calc_result.pricing_method
        invoice.service_charge_percentage_snapshot = calc_result.service_charge_percentage
        invoice.cgst_amount = calc_result.cgst_amount
        invoice.sgst_amount = calc_result.sgst_amount
        invoice.igst_amount = calc_result.igst_amount
        invoice.taxable_amount = calc_result.taxable_amount
        invoice.save()
        
        InvoiceLineItemRepository().create(
            invoice=invoice,
            description=f"Recruitment Service Fee – {candidate_name}",
            quantity=Decimal("1"),
            unit_price=calc_result.taxable_amount,
            line_total=calc_result.taxable_amount,
            created_by_id=created_by_id,
        )
        
        return invoice

    @transaction.atomic
    def generate_for_faculty_placement(
        self, application: FacultyApplication
    ) -> Invoice | None:
        """Deprecated/legacy joining wrapper, delegates to generate_for_selection."""
        return self.generate_for_selection(application)
