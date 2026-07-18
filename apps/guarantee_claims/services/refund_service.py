import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.core.services.base import BaseService
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.guarantee_claims.models.refund import GuaranteeRefund, RefundStatus
from apps.guarantee_claims.constants.enums import ClaimStatus, ClaimResolution
from apps.guarantee_claims.services.workflow_service import GuaranteeClaimWorkflowService

class GuaranteeRefundService(BaseService):
    
    @classmethod
    @transaction.atomic
    def process_refund_approval(cls, claim: GuaranteeClaim, approved_amount: Decimal, admin_id=None, notes: str = "") -> GuaranteeRefund:
        """
        Approves a claim for refund, creating the Refund record and advancing the Claim state.
        Uses the original invoice snapshot to ensure we never refund more than what was paid.
        """
        if claim.status != ClaimStatus.UNDER_REVIEW:
            raise ValueError(f"Claim must be {ClaimStatus.UNDER_REVIEW} to approve a refund.")
            
        from apps.invoices.models import Invoice
        invoice = Invoice.objects.filter(pk=claim.invoice_id).first()
        if not invoice:
            raise ValueError("Associated invoice not found.")
            
        # Validate that refund amount doesn't exceed the original recruitment fee
        # The invoice total amount or taxable amount is the maximum.
        if approved_amount > invoice.total_amount:
            raise ValueError(f"Approved refund ({approved_amount}) cannot exceed original invoice total ({invoice.total_amount}).")

        # Advance state to APPROVED first
        GuaranteeClaimWorkflowService.change_status(
            claim, ClaimStatus.APPROVED, changed_by_id=admin_id, notes="Approved for Refund"
        )
        
        claim.resolution = ClaimResolution.REFUND
        claim.refund_amount = approved_amount
        claim.save(update_fields=['resolution', 'refund_amount'])

        # Now advance to REFUND_PROCESSING
        GuaranteeClaimWorkflowService.change_status(
            claim, ClaimStatus.REFUND_PROCESSING, changed_by_id=admin_id, notes=notes
        )

        prefix = timezone.now().strftime("REF-%Y%m")
        suffix = uuid.uuid4().hex[:8].upper()
        
        refund = GuaranteeRefund.objects.create(
            refund_number=f"{prefix}-{suffix}",
            claim=claim,
            invoice=invoice,
            recruiter_id=claim.recruiter_id,
            institution_id=claim.institution_id,
            original_invoice_amount=invoice.total_amount,
            approved_refund_amount=approved_amount,
            refund_status=RefundStatus.PENDING,
            approved_by_id=admin_id,
            approved_at=timezone.now(),
            notes=notes
        )
        
        return refund

    @classmethod
    @transaction.atomic
    def record_manual_refund_transaction(cls, refund: GuaranteeRefund, transaction_reference: str, payment_provider: str = "manual", admin_id=None, notes: str = ""):
        """
        Records the successful completion of a manual refund transaction using the Provider architecture.
        """
        if refund.refund_status in [RefundStatus.COMPLETED, RefundStatus.CANCELLED, RefundStatus.FAILED]:
            raise ValueError(f"Refund is already {refund.refund_status}")
            
        from apps.guarantee_claims.services.refund_providers.manual import ManualRefundProvider
        
        provider = ManualRefundProvider()
        
        # Advance claim state to REFUNDED
        GuaranteeClaimWorkflowService.change_status(
            refund.claim, ClaimStatus.REFUNDED, changed_by_id=admin_id, notes=f"Refund Transaction: {transaction_reference}"
        )
        
        success = provider.create_refund(
            refund=refund, 
            amount=float(refund.approved_refund_amount), 
            method=payment_provider, 
            transaction_ref=transaction_reference, 
            notes=notes
        )
        
        if success:
            # Here we can add email hooks or celery tasks
            pass
            
        return refund
