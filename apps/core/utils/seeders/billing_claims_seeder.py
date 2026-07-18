from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .base_seeder import BaseSeeder
from apps.invoices.models import Invoice
from apps.billing.models import PlacementFee
from apps.guarantee_claims.services.claim_service import GuaranteeClaimService
from apps.guarantee_claims.constants.enums import (
    ClaimType,
    ClaimStatus,
    ClaimResolution,
)


class BillingClaimsSeeder(BaseSeeder):
    def seed_claims(self):
        self.log("Seeding Guarantee Claims...")
        invoices = list(Invoice.objects.all())
        if not invoices:
            self.log("No invoices found to generate claims from.")
            return

        claim_service = GuaranteeClaimService()

        num_claims = max(1, len(invoices) // 10)
        chosen_invoices = self.faker.random_elements(
            elements=invoices, length=num_claims, unique=True
        )

        for invoice in chosen_invoices:
            exit_date = timezone.now().date() - timedelta(
                days=self.faker.random_int(1, 80)
            )

            try:
                placement_fee = PlacementFee.objects.filter(
                    id=invoice.placement_fee_id
                ).first()
                if not placement_fee:
                    continue

                claim = claim_service.submit(
                    domain=invoice.domain,
                    application_entity_type=placement_fee.entity_type,
                    application_entity_id=placement_fee.entity_id,
                    claim_type=self.faker.random_element(
                        [ClaimType.REFUND, ClaimType.REPLACEMENT]
                    ),
                    reason=self.faker.paragraph(nb_sentences=2),
                    invoice_id=invoice.id,
                    exit_date=exit_date,
                    placement_fee_id=placement_fee.id,
                )

                status = self.faker.random_element(
                    ["submitted", "under_review", "approved", "rejected", "resolved"]
                )
                if status in ["under_review", "approved", "rejected", "resolved"]:
                    claim_service.review(claim, review_notes="Looking into this claim.")

                if status in ["approved", "resolved"]:
                    resolution = (
                        ClaimResolution.REFUND
                        if claim.claim_type == ClaimType.REFUND
                        else ClaimResolution.REPLACEMENT_SEARCH
                    )
                    claim_service.approve(
                        claim, resolution=resolution, review_notes="Claim approved."
                    )

                if status == "resolved":
                    claim_service.resolve(claim, review_notes="Claim fully resolved.")

                if status == "rejected":
                    claim_service.reject(
                        claim, review_notes="Did not meet policy requirements."
                    )

            except Exception as e:
                self.log(f"Failed to create claim for invoice {invoice.id}: {e}")

    def seed_all(self):
        self.seed_claims()
