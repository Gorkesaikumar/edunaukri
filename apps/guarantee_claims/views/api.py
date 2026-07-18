import json
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.constants.enums import DomainType
from apps.invoices.models import Invoice
from apps.guarantee_claims.services.claim_service import GuaranteeClaimService


class RecruiterGuaranteeClaimAPIView(LoginRequiredMixin, View):
    """API for recruiters to file guarantee claims against invoices."""

    def post(self, request, *args, **kwargs):
        user = WebJWTService.get_valid_it_user(request)
        domain = DomainType.IT
        if not user:
            user = WebJWTService.get_valid_college_user(request)
            domain = DomainType.FACULTY

        if not user:
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)

        try:
            data = json.loads(request.body)
            invoice_id = data.get("invoice_id")
            exit_date = data.get("exit_date")
            reason = data.get("reason")
            resolution = data.get(
                "resolution"
            )  # The requested resolution (e.g., refund vs replacement)

            if domain == DomainType.IT:
                from apps.companies.selectors.company_selector import (
                    CompanyMemberSelector,
                )

                entity_ids = CompanyMemberSelector().get_company_ids_for_user(user.pk)
            else:
                from apps.colleges.selectors.college_selector import (
                    CollegeMemberSelector,
                )

                entity_ids = CollegeMemberSelector().get_college_ids_for_user(user.pk)

            invoice = get_object_or_404(
                Invoice,
                pk=invoice_id,
                is_deleted=False,
                bill_to_entity_id__in=entity_ids,
            )

            # Use the GuaranteeClaimService to submit
            service = GuaranteeClaimService()
            claim = service.submit(
                domain=domain,
                application_entity_type="company"
                if domain == DomainType.IT
                else "college",
                application_entity_id=invoice.bill_to_entity_id,
                claim_type="exit",  # Assume exit for now
                reason=f"Preferred Resolution: {resolution}. Reason: {reason}",
                invoice_id=invoice.id,
                exit_date=exit_date,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Claim submitted successfully.",
                    "claim_id": str(claim.pk),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
