from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.services.base import BaseService
from apps.guarantee_claims.models.claim import GuaranteeClaim, GuaranteeClaimHistory
from apps.guarantee_claims.constants.enums import ClaimStatus

class GuaranteeClaimWorkflowService(BaseService):
    
    VALID_TRANSITIONS = {
        ClaimStatus.DRAFT: [ClaimStatus.SUBMITTED, ClaimStatus.CANCELLED],
        ClaimStatus.SUBMITTED: [ClaimStatus.UNDER_REVIEW, ClaimStatus.REJECTED],
        ClaimStatus.UNDER_REVIEW: [ClaimStatus.MORE_INFORMATION_REQUIRED, ClaimStatus.APPROVED, ClaimStatus.REJECTED],
        ClaimStatus.MORE_INFORMATION_REQUIRED: [ClaimStatus.UNDER_REVIEW, ClaimStatus.REJECTED],
        ClaimStatus.APPROVED: [ClaimStatus.REFUND_PROCESSING, ClaimStatus.REPLACEMENT_SEARCH],
        ClaimStatus.REFUND_PROCESSING: [ClaimStatus.REFUNDED],
        ClaimStatus.REPLACEMENT_SEARCH: [ClaimStatus.REPLACEMENT_COMPLETED],
        ClaimStatus.REFUNDED: [ClaimStatus.RESOLVED],
        ClaimStatus.REPLACEMENT_COMPLETED: [ClaimStatus.RESOLVED],
        # End states
        ClaimStatus.REJECTED: [],
        ClaimStatus.RESOLVED: [],
        ClaimStatus.CANCELLED: [],
    }

    @classmethod
    @transaction.atomic
    def change_status(cls, claim: GuaranteeClaim, new_status: str, changed_by_id=None, notes: str = "") -> GuaranteeClaim:
        if claim.status == new_status:
            return claim

        allowed = cls.VALID_TRANSITIONS.get(claim.status, [])
        if new_status not in allowed:
            raise ValidationError(f"Invalid state transition from {claim.status} to {new_status}")

        old_status = claim.status
        claim.status = new_status
        
        # Auto-update timestamp fields based on status
        if new_status == ClaimStatus.UNDER_REVIEW and not claim.reviewed_at:
            claim.reviewed_at = timezone.now()
        elif new_status == ClaimStatus.APPROVED:
            claim.approval_date = timezone.now()
            claim.approved_by_id = changed_by_id
        elif new_status == ClaimStatus.RESOLVED:
            claim.resolved_at = timezone.now()
            
        claim.save()
        
        GuaranteeClaimHistory.objects.create(
            claim=claim,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=changed_by_id,
            notes=notes
        )
        
        return claim
