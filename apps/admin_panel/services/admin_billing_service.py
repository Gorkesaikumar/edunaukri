from apps.admin_panel.services.admin_audit import record_admin_action
from apps.core.services.base import BaseService
from apps.guarantee_claims.services.claim_service import GuaranteeClaimService
from apps.invoices.services.invoice_lifecycle_service import InvoiceLifecycleService
from apps.invoices.services.refund_service import RefundService
from apps.invoices.selectors.invoice_selector import FinancialStatisticsSelector


class AdminInvoiceService(BaseService):
    def __init__(self):
        self.lifecycle = InvoiceLifecycleService()
        self.refund = RefundService()
        self.stats = FinancialStatisticsSelector()

    def financial_summary(self, **filters) -> dict:
        return self.stats.summary(**filters)

    def cancel_invoice(self, invoice, *, admin_id, notes: str = ""):
        invoice = self.lifecycle.cancel(invoice, notes=notes)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.invoice.cancelled",
            entity_type="billing_invoice",
            entity_id=invoice.pk,
            payload={"invoice_number": invoice.invoice_number},
        )
        return invoice

    def refund_invoice(self, invoice, *, admin_id, amount, reason: str, **kwargs):
        refund = self.refund.refund(invoice, amount=amount, reason=reason, **kwargs)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.invoice.refunded",
            entity_type="billing_invoice",
            entity_id=invoice.pk,
            payload={"amount": str(amount), "reason": reason},
        )
        return refund

    def mark_overdue(self, invoice, *, admin_id, notes: str = ""):
        invoice = self.lifecycle.mark_overdue(invoice)
        if invoice:
            record_admin_action(
                admin_id=admin_id,
                event_type="admin.invoice.marked_overdue",
                entity_type="billing_invoice",
                entity_id=invoice.pk,
                payload={"invoice_number": invoice.invoice_number},
            )
        return invoice

    def mark_paid(self, invoice, *, admin_id, notes: str = ""):
        from apps.invoices.services.payment_tracking_service import (
            PaymentTrackingService,
        )

        payment_service = PaymentTrackingService()
        amount = invoice.total_amount - (invoice.amount_paid or 0)
        payment = payment_service.record_payment(
            invoice=invoice,
            amount=amount,
            payment_method="admin_manual",
            notes=notes or "Marked as paid by admin",
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.invoice.marked_paid",
            entity_type="billing_invoice",
            entity_id=invoice.pk,
            payload={"invoice_number": invoice.invoice_number, "amount": str(amount)},
        )
        return invoice


class AdminGuaranteeService(BaseService):
    def __init__(self):
        self.claims = GuaranteeClaimService()

    def approve_claim(
        self, claim, *, admin_id, resolution: str, review_notes: str = ""
    ):
        claim = self.claims.approve(
            claim, resolution=resolution, review_notes=review_notes
        )
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.guarantee_claim.approved",
            entity_type="guarantee_claim",
            entity_id=claim.pk,
            payload={"claim_number": claim.claim_number, "resolution": resolution},
        )
        return claim

    def reject_claim(self, claim, *, admin_id, review_notes: str = ""):
        claim = self.claims.reject(claim, review_notes=review_notes)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.guarantee_claim.rejected",
            entity_type="guarantee_claim",
            entity_id=claim.pk,
            payload={"claim_number": claim.claim_number},
        )
        return claim

    def resolve_claim(self, claim, *, admin_id, review_notes: str = ""):
        claim = self.claims.resolve(claim, review_notes=review_notes)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.guarantee_claim.resolved",
            entity_type="guarantee_claim",
            entity_id=claim.pk,
            payload={"claim_number": claim.claim_number},
        )
        return claim


class AdminFeeScheduleService(BaseService):
    def __init__(self):
        from apps.billing.services.placement_fee_service import FeeScheduleService

        self.fee_schedules = FeeScheduleService()

    def create_schedule(self, *, data: dict, admin_id):
        schedule = self.fee_schedules.create_schedule(data=data, created_by_id=admin_id)
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.fee_schedule.created",
            entity_type="fee_schedule",
            entity_id=schedule.pk,
            payload={"domain": schedule.domain, "name": schedule.name},
        )
        return schedule
