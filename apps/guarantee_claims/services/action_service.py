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
            "VIEW_RECRUITER",
            "REVIEW_CLAIM",
        ]

        if claim.status in [ClaimStatus.SUBMITTED, ClaimStatus.UNDER_REVIEW, ClaimStatus.MORE_INFORMATION_REQUIRED]:
            actions.append("APPROVE_CLAIM")
            actions.append("REJECT_CLAIM")

        if claim.invoice_id:
            actions.extend(["VIEW_INVOICE", "DOWNLOAD_INVOICE"])

        if claim.status == ClaimStatus.APPROVED:
            if claim.resolution == ClaimResolution.REFUND or claim.claim_type == "refund":
                actions.append("PROCESS_REFUND")
            else:
                actions.append("RESOLVE_CLAIM")
        elif claim.status == ClaimStatus.REFUND_PROCESSING:
            actions.append("MARK_REFUNDED")
            if hasattr(claim, 'refunds') and claim.refunds.exists():
                actions.append("VIEW_REFUND")
        elif claim.status == ClaimStatus.REFUNDED:
            actions.append("RESOLVE_CLAIM")
            if hasattr(claim, 'refunds') and claim.refunds.exists():
                actions.append("VIEW_REFUND")
        elif claim.status == ClaimStatus.RESOLVED:
            if hasattr(claim, 'refunds') and claim.refunds.exists():
                actions.append("VIEW_REFUND")

        return actions
