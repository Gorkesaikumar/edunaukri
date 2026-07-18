from django.contrib import admin

from apps.invoices.models import (
    Invoice,
    InvoiceLineItem,
    InvoiceStatusHistory,
    PaymentRecord,
    RefundRecord,
)


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = ("id",)


class InvoiceStatusHistoryInline(admin.TabularInline):
    model = InvoiceStatusHistory
    extra = 0
    readonly_fields = (
        "from_status",
        "to_status",
        "changed_by_id",
        "notes",
        "changed_at",
    )
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "bill_to_name_snapshot",
        "status",
        "total_amount",
        "amount_paid",
        "issued_at",
        "due_at",
    )
    list_filter = ("domain", "status", "is_deleted")
    search_fields = ("invoice_number", "bill_to_name_snapshot")
    inlines = [InvoiceLineItemInline, InvoiceStatusHistoryInline]
    readonly_fields = ("invoice_number", "placement_fee_id")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_method", "status", "paid_at")
    list_filter = ("status", "payment_method")


@admin.register(RefundRecord)
class RefundRecordAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "reason", "refunded_at", "processed_by_id")
