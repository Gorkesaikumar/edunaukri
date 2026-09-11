import uuid
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.guarantee_claims.models.claim import GuaranteeClaim, GuaranteeClaimHistory
from apps.guarantee_claims.models.refund import GuaranteeRefund, RefundStatus
from apps.guarantee_claims.constants.enums import ClaimStatus, ClaimResolution, ExitReason
from apps.guarantee_claims.services.action_service import GuaranteeClaimActionService
from apps.guarantee_claims.services.workflow_service import GuaranteeClaimWorkflowService
from apps.guarantee_claims.services.refund_service import GuaranteeRefundService
from apps.admin_panel.views.web import SuperAdminGuaranteeClaimActionView, SuperAdminGuaranteeClaimsView
from apps.admin_panel.views.claim_api import SuperAdminClaimCandidateSummaryAPIView
from apps.invoices.models import Invoice

User = get_user_model()


from django.test import TestCase

class TestGuaranteeClaimApprovalWorkflow(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superadmin = User.objects.create_superuser(
            email="superadmin.claims@example.com",
            password="Password123!",
        )
        self.regular_user = User.objects.create_user(
            email="recruiter.regular@example.com",
            password="Password123!",
        )

        self.invoice = Invoice.objects.create(
            placement_fee_id=uuid.uuid4(),
            total_amount=Decimal("25000.00"),
        )

        self.claim = GuaranteeClaim.objects.create(
            claim_number="GC-TEST-001",
            domain=DomainType.IT,
            application_entity_type=EntityReferenceType.JOB_APPLICATION,
            application_entity_id=uuid.uuid4(),
            invoice_id=self.invoice.id,
            joining_date=timezone.now().date() - timedelta(days=30),
            guarantee_start_date=timezone.now().date() - timedelta(days=30),
            guarantee_end_date=timezone.now().date() + timedelta(days=60),
            exit_date=timezone.now().date() - timedelta(days=5),
            exit_reason=ExitReason.RESIGNED,
            claim_type="refund",
            status=ClaimStatus.SUBMITTED,
            reason="Candidate resigned after 25 days due to personal reasons.",
        )

    def test_action_availability_mapping(self):
        actions = GuaranteeClaimActionService.get_available_actions(self.claim)
        assert "APPROVE_CLAIM" in actions
        assert "REJECT_CLAIM" in actions
        assert "REVIEW_CLAIM" in actions

    def test_superadmin_can_approve_claim(self):
        view = SuperAdminGuaranteeClaimActionView.as_view()
        request = self.factory.post(
            f"/super-admin/claims/{self.claim.id}/action/",
            data={"action": "approve", "notes": "Approved after verification"},
            content_type="application/json",
        )
        request.user = self.superadmin
        response = view(request, claim_id=self.claim.id)
        assert response.status_code == 200

        self.claim.refresh_from_db()
        assert self.claim.status == ClaimStatus.REFUND_PROCESSING
        assert self.claim.approved_by_id == self.superadmin.id
        assert self.claim.admin_notes == "Approved after verification"

        refund = GuaranteeRefund.objects.filter(claim_id=self.claim.id).first()
        assert refund is not None
        assert refund.approved_refund_amount == Decimal("25000.00")

    def test_superadmin_can_reject_claim(self):
        view = SuperAdminGuaranteeClaimActionView.as_view()
        request = self.factory.post(
            f"/super-admin/claims/{self.claim.id}/action/",
            data={"action": "reject", "notes": "Candidate exit occurred past 90 days policy"},
            content_type="application/json",
        )
        request.user = self.superadmin
        response = view(request, claim_id=self.claim.id)
        assert response.status_code == 200

        self.claim.refresh_from_db()
        assert self.claim.status == ClaimStatus.REJECTED
        assert self.claim.admin_notes == "Candidate exit occurred past 90 days policy"

    def test_rejection_requires_reason(self):
        view = SuperAdminGuaranteeClaimActionView.as_view()
        request = self.factory.post(
            f"/super-admin/claims/{self.claim.id}/action/",
            data={"action": "reject", "notes": ""},
            content_type="application/json",
        )
        request.user = self.superadmin
        response = view(request, claim_id=self.claim.id)
        assert response.status_code == 200
        import json
        res_data = json.loads(response.content)
        assert res_data["success"] is False
        assert "required" in res_data["error"]

    def test_duplicate_approval_prevented(self):
        # First approval
        self.claim.status = ClaimStatus.APPROVED
        self.claim.save()

        view = SuperAdminGuaranteeClaimActionView.as_view()
        request = self.factory.post(
            f"/super-admin/claims/{self.claim.id}/action/",
            data={"action": "approve", "notes": "Second attempt"},
            content_type="application/json",
        )
        request.user = self.superadmin
        response = view(request, claim_id=self.claim.id)
        import json
        res_data = json.loads(response.content)
        assert res_data["success"] is False
        assert "already been approved" in res_data["error"]

    def test_unauthorized_user_blocked(self):
        view = SuperAdminGuaranteeClaimActionView.as_view()
        request = self.factory.post(
            f"/super-admin/claims/{self.claim.id}/action/",
            data={"action": "approve", "notes": "Unauthorized attempt"},
            content_type="application/json",
        )
        request.user = self.regular_user
        response = view(request, claim_id=self.claim.id)
        # SuperAdminPortalMixin returns 403 or redirect for non-superuser
        assert response.status_code in [403, 302]
