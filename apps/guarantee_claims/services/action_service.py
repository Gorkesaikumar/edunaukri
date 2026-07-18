from typing import List
from apps.core.services.base import BaseService
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.guarantee_claims.constants.enums import ClaimStatus, ClaimResolution

class GuaranteeClaimActionService(BaseService):
    
    @classmethod
    def get_available_actions(cls, claim: GuaranteeClaim) -> List[str]:
        """
        Returns a list of action keys available for a given claim based on its state.
        """
        actions = [
            "VIEW_CANDIDATE",
            "VIEW_RECRUITER"
        ]
        
        if claim.status == ClaimStatus.SUBMITTED:
            actions.append("VIEW_CLAIM")
        
        if claim.invoice_id:
            actions.extend(["VIEW_INVOICE", "DOWNLOAD_INVOICE"])
            
        # Refund processing actions
        if claim.status == ClaimStatus.APPROVED and claim.resolution == ClaimResolution.REFUND:
            actions.append("PROCESS_REFUND")
        elif claim.status in [ClaimStatus.REFUND_PROCESSING, ClaimStatus.REFUNDED, ClaimStatus.RESOLVED]:
            # Only show view refund details if a refund record exists
            if hasattr(claim, 'refunds') and claim.refunds.exists():
                actions.append("VIEW_REFUND")
                
        return actions
