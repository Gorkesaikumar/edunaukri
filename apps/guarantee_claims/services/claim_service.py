import uuid
from django.db import transaction
from django.utils import timezone
from apps.core.services.base import BaseService
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.guarantee_claims.services.eligibility_service import GuaranteeClaimEligibilityService
from apps.guarantee_claims.constants.enums import ClaimStatus

class GuaranteeClaimService(BaseService):
    
    @classmethod
    @transaction.atomic
    def submit_claim(cls, domain: str, recruiter_id: str, institution_id: str, application, exit_date, exit_reason: str, claim_type: str, reason: str) -> GuaranteeClaim:
        """
        Submits a new guarantee claim for a given application (Faculty or IT).
        Enforces strict eligibility criteria before creating the record.
        """
        # Validate Eligibility
        eligibility = GuaranteeClaimEligibilityService().check_eligibility(application, exit_date)
        if not eligibility["eligible"]:
            raise ValueError(f"Claim submission failed: {eligibility['reason']}")
            
        # Additional deep relational integrity checks
        from apps.applications.models.application import PlacementDetails
        placement = PlacementDetails.objects.filter(application_id=application.pk, domain=domain, is_deleted=False).first()
        if not placement:
            raise ValueError("Claim submission failed: Candidate placement record is missing or invalid.")
        
        if not placement.actual_joining_date:
            raise ValueError("Claim submission failed: Candidate joining status is not confirmed.")

        invoice = eligibility["invoice"]
        
        prefix = "CLM-" + timezone.now().strftime("%Y%m")
        suffix = uuid.uuid4().hex[:8].upper()
        claim_number = f"{prefix}-{suffix}"
        
        claim = GuaranteeClaim.objects.create(
            claim_number=claim_number,
            domain=domain,
            recruiter_id=recruiter_id,
            institution_id=institution_id,
            application_entity_type=application._meta.model_name,
            application_entity_id=application.pk,
            placement_fee_id=application.pk,
            invoice_id=invoice.pk,
            joining_date=eligibility["joining_date"],
            guarantee_start_date=eligibility["joining_date"],
            guarantee_end_date=eligibility["guarantee_end_date"],
            exit_date=exit_date,
            exit_reason=exit_reason,
            claim_type=claim_type,
            reason=reason,
            status=ClaimStatus.SUBMITTED
        )
        
        # In a real system, emit a notification event here for the Super Admin
        # from apps.notifications.services import NotificationService
        # NotificationService.notify_super_admin(f"New Guarantee Claim submitted: {claim_number}")
        
        return claim
