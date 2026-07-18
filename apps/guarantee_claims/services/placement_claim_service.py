import uuid
from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.applications.models import FacultyApplication
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.core.services.base import BaseService
from apps.guarantee_claims.constants.enums import PlacementClaimStatus
from apps.guarantee_claims.models.placement_claim import PlacementClaim, PlacementClaimHistory
from apps.invoices.models import Invoice, PaymentRecord
from apps.invoices.constants.enums import PaymentStatus


class PlacementClaimService(BaseService):
    """Service to handle placement claims submitted by faculty recruiters."""

    @transaction.atomic
    def submit_claim(
        self,
        application,
        recruiter_id: uuid.UUID,
        data: dict
    ) -> PlacementClaim:
        from apps.applications.models import FacultyApplication, JobApplication
        from apps.applications.constants.faculty_enums import FacultyApplicationStatus
        from apps.applications.constants.enums import JobApplicationStatus
        from apps.guarantee_claims.models import PlacementGuarantee
        from apps.guarantee_claims.constants.enums import GuaranteeStatus
        
        is_faculty = isinstance(application, FacultyApplication)
        
        # 1. Validate application is joined
        if is_faculty:
            if application.status != FacultyApplicationStatus.JOINED or not application.joined_at:
                raise ValidationError("Claim can only be submitted for candidates who have joined.")
            claim_deadline = application.joined_at.date() + timedelta(days=90)
        else:
            if application.status != JobApplicationStatus.JOINED or not application.joined_at:
                raise ValidationError("Claim can only be submitted for candidates who have joined.")
            claim_deadline = application.joined_at.date() + timedelta(days=90)

        # 2. Validate 90-day window
        current_date = timezone.now().date()
        if current_date > claim_deadline:
            raise ValidationError("The 90-day claim protection period has expired.")
            
        # 3. Prevent duplicate active claims
        existing_filter = {
            "status__in": [
                PlacementClaimStatus.DRAFT,
                PlacementClaimStatus.SUBMITTED,
                PlacementClaimStatus.UNDER_REVIEW,
                PlacementClaimStatus.MORE_INFORMATION_REQUIRED,
                PlacementClaimStatus.APPROVED,
                PlacementClaimStatus.REFUND_PENDING,
                PlacementClaimStatus.REFUND_PROCESSING,
                PlacementClaimStatus.REFUNDED
            ]
        }
        if is_faculty:
            existing_filter["application"] = application
        else:
            existing_filter["job_application"] = application
            
        existing_claim = PlacementClaim.objects.filter(**existing_filter).first()
        if existing_claim:
            raise ValidationError("An active claim already exists for this placement.")

        # 5. Fetch related invoice if exists
        from apps.billing.models.fee import PlacementFee
        fee = PlacementFee.objects.filter(entity_id=application.pk, is_deleted=False).first()
        invoice = Invoice.objects.filter(placement_fee_id=fee.pk, is_deleted=False).first() if fee else None

        # 6. Create claim
        create_kwargs = {
            "claim_number": self._generate_claim_number(),
            "invoice": invoice,
            "faculty_recruiter_id": recruiter_id,
            "claim_reason": data["claim_reason"],
            "claim_type": data.get("claim_type", "refund"),
            "incident_date": data["incident_date"],
            "claim_description": data["claim_description"],
            "supporting_documents": data.get("supporting_documents", []),
            "status": PlacementClaimStatus.UNDER_REVIEW,
        }
        if is_faculty:
            create_kwargs["application"] = application
            create_kwargs["institution"] = application.vacancy.college
        else:
            create_kwargs["job_application"] = application
            create_kwargs["company_id"] = application.job_posting.company_id
            
        claim = PlacementClaim.objects.create(**create_kwargs)

        self._record_history(claim, None, PlacementClaimStatus.UNDER_REVIEW, "Claim submitted by recruiter")
        
        # 7. Transition guarantee status to CLAIMED
        if invoice:
            guarantee = PlacementGuarantee.objects.filter(invoice_id=invoice.pk, is_deleted=False).first()
            if guarantee:
                guarantee.status = GuaranteeStatus.CLAIMED
                guarantee.save(update_fields=["status"])
                
        return claim




    @transaction.atomic
    def approve_claim(self, claim: PlacementClaim, admin_id: uuid.UUID) -> PlacementClaim:
        if claim.status not in [PlacementClaimStatus.UNDER_REVIEW, PlacementClaimStatus.MORE_INFORMATION_REQUIRED]:
            raise ValidationError("Only claims under review can be approved.")

        eligible_amount = self.calculate_refund_eligibility(claim)
        
        claim.status = PlacementClaimStatus.APPROVED
        claim.approved_at = timezone.now()
        claim.reviewed_by_id = admin_id
        claim.refund_amount = eligible_amount
        claim.save(update_fields=["status", "approved_at", "reviewed_by_id", "refund_amount", "updated_at"])

        self._record_history(claim, claim.status, PlacementClaimStatus.APPROVED, "Claim approved by admin")

        # Transition to REFUND_PENDING
        claim.status = PlacementClaimStatus.REFUND_PENDING
        claim.save(update_fields=["status", "updated_at"])
        self._record_history(claim, PlacementClaimStatus.APPROVED, PlacementClaimStatus.REFUND_PENDING, "Refund pending processing")
        
        # TODO: Notify Recruiter
        return claim

    @transaction.atomic
    def reject_claim(self, claim: PlacementClaim, admin_id: uuid.UUID, notes: str) -> PlacementClaim:
        if not notes:
            raise ValidationError("Rejection reason is required.")
            
        current_status = claim.status
        claim.status = PlacementClaimStatus.REJECTED
        claim.rejected_at = timezone.now()
        claim.reviewed_by_id = admin_id
        claim.admin_notes = notes
        claim.save(update_fields=["status", "rejected_at", "reviewed_by_id", "admin_notes", "updated_at"])

        self._record_history(claim, current_status, PlacementClaimStatus.REJECTED, notes)
        
        # TODO: Notify Recruiter
        return claim

    def calculate_refund_eligibility(self, claim: PlacementClaim) -> Decimal:
        """Calculates maximum refundable amount based on actual payments made."""
        if not claim.invoice:
            return Decimal("0.00")
            
        # Get all successful payments for this invoice
        payments = PaymentRecord.objects.filter(
            invoice=claim.invoice,
            status=PaymentStatus.PAID
        ).aggregate(total_paid=models.Sum('amount'))['total_paid'] or Decimal("0.00")
        
        # Check if there are any other refunds already processed for this invoice
        from apps.invoices.models import RefundRecord
        refunds = RefundRecord.objects.filter(
            invoice=claim.invoice
        ).aggregate(total_refunded=models.Sum('amount'))['total_refunded'] or Decimal("0.00")
        
        eligible_amount = payments - refunds
        return max(eligible_amount, Decimal("0.00"))

    def _generate_claim_number(self) -> str:
        prefix = timezone.now().strftime("CLM-%Y%m")
        suffix = uuid.uuid4().hex[:8].upper()
        return f"{prefix}-{suffix}"

    def _record_history(self, claim: PlacementClaim, from_status: str | None, to_status: str, notes: str = ""):
        PlacementClaimHistory.objects.create(
            claim=claim,
            from_status=from_status,
            to_status=to_status,
            notes=notes
        )
