"""Billing domain event types consumed from the outbox."""

BILLING_PLACEMENT_EVENT_TYPES = frozenset(
    {
        "application.hired",
        "application.joined",
        "application.placed",
    }
)

INVOICE_EVENT_TYPES = frozenset(
    {
        "invoice.issued",
        "invoice.paid",
        "invoice.cancelled",
        "invoice.refunded",
    }
)

GUARANTEE_EVENT_TYPES = frozenset(
    {
        "claim.submitted",
        "claim.approved",
        "claim.rejected",
        "claim.resolved",
    }
)
