from django.db import models
from django.utils import timezone
from apps.core.models.base import AuditedBaseModel
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.invoices.models import Invoice

class RefundStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"

class GuaranteeRefund(AuditedBaseModel):
    refund_number = models.CharField(max_length=50, unique=True)
    claim = models.ForeignKey(GuaranteeClaim, on_delete=models.PROTECT, related_name="refunds")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="guarantee_refunds")
    
    # Recruiter IDs (either IT recruiter or Faculty institution)
    recruiter_id = models.UUIDField(null=True, blank=True, db_index=True)
    institution_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    original_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    refund_status = models.CharField(
        max_length=30,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        db_index=True
    )
    
    payment_provider = models.CharField(max_length=50, blank=True, help_text="e.g. manual, razorpay, stripe")
    provider_refund_id = models.CharField(max_length=100, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)
    
    approved_by_id = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    failure_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "billing_guarantee_refund"
        ordering = ["-created_at"]

    def __str__(self):
        return self.refund_number
