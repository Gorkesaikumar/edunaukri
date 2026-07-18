from django.db import models


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending"
    ISSUED = "issued", "Issued"
    PARTIALLY_PAID = "partially_paid", "Partially Paid"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"
    OVERDUE = "overdue", "Overdue"
    REFUNDED = "refunded", "Refunded"
    VOID = "void", "Void"


class PaymentMethod(models.TextChoices):
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    CHEQUE = "cheque", "Cheque"
    UPI = "upi", "UPI"
    CASH = "cash", "Cash"
    OTHER = "other", "Other"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"


TERMINAL_INVOICE_STATUSES = frozenset(
    {
        InvoiceStatus.PAID,
        InvoiceStatus.CANCELLED,
        InvoiceStatus.REFUNDED,
        InvoiceStatus.VOID,
    }
)
