from django.utils import timezone
from apps.guarantee_claims.services.refund_providers.base import RefundProvider
from apps.guarantee_claims.models.refund import GuaranteeRefund, RefundStatus
from apps.guarantee_claims.models.claim import ClaimStatus

class ManualRefundProvider(RefundProvider):
    """
    Handles manual off-platform refunds (Bank Transfer, UPI, Cheque).
    Requires a human to record the transaction reference.
    """
    
    def create_refund(self, refund: GuaranteeRefund, amount: float, method: str, transaction_ref: str = None, notes: str = None) -> bool:
        refund.payment_provider = "MANUAL"
        refund.transaction_reference = transaction_ref
        refund.notes = f"Manual Method: {method}\n{notes}".strip()
        refund.refund_status = RefundStatus.COMPLETED
        refund.processed_at = timezone.now()
        refund.completed_at = timezone.now()
        refund.save()
        
        # Sync claim status
        claim = refund.claim
        claim.status = ClaimStatus.REFUNDED
        claim.save()
        
        return True
        
    def get_refund_status(self, refund: GuaranteeRefund) -> str:
        return refund.refund_status
        
    def verify_refund(self, refund: GuaranteeRefund) -> bool:
        # Manual refunds are verified by the admin providing the transaction reference
        return bool(refund.transaction_reference)
