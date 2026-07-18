from rest_framework import serializers

from apps.invoices.constants.enums import PaymentMethod
from apps.invoices.models import Invoice, PaymentRecord


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "domain",
            "placement_fee_id",
            "bill_to_entity_type",
            "bill_to_entity_id",
            "bill_to_name_snapshot",
            "status",
            "subtotal",
            "tax_amount",
            "total_amount",
            "amount_paid",
            "currency",
            "issued_at",
            "due_at",
            "paid_at",
            "cancelled_at",
            "refunded_at",
            "pdf_metadata",
            "notes",
            "created_at",
        )
        read_only_fields = fields


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = (
            "id",
            "invoice",
            "amount",
            "payment_method",
            "status",
            "reference_number",
            "paid_at",
            "notes",
            "created_at",
        )
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class InvoiceGenerateSerializer(serializers.Serializer):
    placement_fee_id = serializers.UUIDField()


class InvoiceCancelSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class InvoiceRefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField()
    reference_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
