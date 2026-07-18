from apps.core.selectors.read import ReadSelector
from apps.guarantee_claims.models import GuaranteeClaim


class GuaranteeClaimSelector(ReadSelector):
    model = GuaranteeClaim

    def list_by_domain(
        self, domain: str | None = None, *, status: str | None = None, invoice_id=None
    ):
        queryset = self.list_all(order_by="-submitted_at")
        if domain:
            queryset = queryset.filter(domain=domain)
        if status:
            queryset = queryset.filter(status=status)
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset

    def get_active(self, claim_id):
        return self.filter_by(pk=claim_id).first()
