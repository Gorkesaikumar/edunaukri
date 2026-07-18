from django.db import models
from django.utils import timezone

from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.core.models.base import AuditedBaseModel
from apps.invoices.constants.enums import InvoiceStatus, PaymentMethod, PaymentStatus


class Invoice(AuditedBaseModel):
    invoice_number = models.CharField(max_length=50, unique=True)
    domain = models.CharField(max_length=20, choices=DomainType.choices, db_index=True)
    placement_fee_id = models.UUIDField(null=True, blank=True, db_index=True)
    bill_to_entity_type = models.CharField(
        max_length=40, choices=EntityReferenceType.choices
    )
    bill_to_entity_id = models.UUIDField(db_index=True)
    bill_to_name_snapshot = models.CharField(max_length=300)
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="INR")
    
    # Financial Snapshot Fields (Preserve calculation rates at time of generation)
    candidate_annual_ctc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    candidate_name = models.CharField(max_length=200, blank=True)
    candidate_job_title = models.CharField(max_length=200, blank=True)
    pricing_method_snapshot = models.CharField(max_length=50, blank=True)
    service_charge_percentage_snapshot = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    pdf_metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "billing_invoice"
        constraints = [
            models.UniqueConstraint(
                fields=["placement_fee_id"],
                condition=models.Q(is_deleted=False, placement_fee_id__isnull=False),
                name="unique_active_invoice_per_placement_fee",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "domain"]),
            models.Index(fields=["bill_to_entity_type", "bill_to_entity_id"]),
            models.Index(fields=["due_at"]),
            models.Index(fields=["issued_at"]),
            models.Index(fields=["paid_at"]),
        ]

    def __str__(self):
        return self.invoice_number


class InvoiceLineItem(AuditedBaseModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "billing_invoice_line_item"


class PaymentRecord(AuditedBaseModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PAID,
        db_index=True,
    )
    reference_number = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    recorded_by_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "billing_payment_record"


class InvoiceStatusHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="status_history"
    )
    from_status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=20, choices=InvoiceStatus.choices)
    changed_by_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "billing_invoice_status_history"
        ordering = ["-changed_at"]


class RefundRecord(AuditedBaseModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="refunds"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    reference_number = models.CharField(max_length=100, blank=True)
    refunded_at = models.DateTimeField(default=timezone.now)
    processed_by_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "billing_refund_record"
