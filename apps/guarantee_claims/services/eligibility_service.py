from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.services.base import BaseService
from apps.guarantee_claims.constants.enums import DEFAULT_GUARANTEE_DAYS

class GuaranteeClaimEligibilityService(BaseService):
    def __init__(self):
        pass

    def check_eligibility(self, application, exit_date) -> dict:
        """
        Validates if an application (Faculty or IT) is eligible for a guarantee claim.
        Returns a dictionary with 'eligible' (bool), 'guarantee_end_date', 'joining_date', and 'reason'.
        """
        from apps.applications.models import FacultyApplication, JobApplication
        from apps.core.constants.enums import ApplicationStatus
        
        # 1. Candidate must have joined
        if not application or application.status != ApplicationStatus.JOINED:
            return {"eligible": False, "reason": "Candidate has not reached JOINED status."}

        # 2. Joining date must be confirmed
        joining_date = None
        if isinstance(application, FacultyApplication):
            joining_date = application.joined_date
        elif isinstance(application, JobApplication):
            joining_date = getattr(application, 'actual_joining_date', getattr(application, 'joining_date', None))

        if not joining_date:
            return {"eligible": False, "reason": "Joining date is not confirmed."}

        # 3. Guarantee period calculation
        guarantee_end_date = joining_date + timedelta(days=DEFAULT_GUARANTEE_DAYS)

        # 4. Exit date within the 90-day window
        if exit_date > guarantee_end_date:
            return {
                "eligible": False, 
                "reason": f"Exit date ({exit_date}) is outside the {DEFAULT_GUARANTEE_DAYS}-day guarantee window (ended on {guarantee_end_date}).",
                "guarantee_end_date": guarantee_end_date,
                "joining_date": joining_date
            }
            
        if exit_date < joining_date:
            return {
                "eligible": False,
                "reason": "Exit date cannot be before the joining date.",
                "guarantee_end_date": guarantee_end_date,
                "joining_date": joining_date
            }

        # 5. Must have a valid invoice
        from apps.invoices.models import Invoice
        invoice = Invoice.objects.filter(
            placement_fee_id=application.pk,
            is_deleted=False
        ).first()

        if not invoice:
            return {
                "eligible": False, 
                "reason": "No active recruitment invoice found for this placement.",
                "guarantee_end_date": guarantee_end_date,
                "joining_date": joining_date
            }

        # 6. No existing active claim for this placement
        from apps.guarantee_claims.models.claim import GuaranteeClaim
        from apps.guarantee_claims.constants.enums import ClaimStatus
        active_claims = GuaranteeClaim.objects.filter(
            application_entity_id=application.pk,
            is_deleted=False
        ).exclude(status__in=[ClaimStatus.REJECTED, ClaimStatus.CANCELLED, ClaimStatus.RESOLVED])
        
        if active_claims.exists():
            return {
                "eligible": False, 
                "reason": "An active guarantee claim already exists for this placement.",
                "guarantee_end_date": guarantee_end_date,
                "joining_date": joining_date
            }

        return {
            "eligible": True,
            "reason": "Eligible for guarantee claim.",
            "guarantee_end_date": guarantee_end_date,
            "joining_date": joining_date,
            "invoice": invoice
        }
