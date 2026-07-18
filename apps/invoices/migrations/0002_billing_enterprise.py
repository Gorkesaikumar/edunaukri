# Generated manually for billing enterprise module

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="pdf_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="invoice",
            name="refunded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending", "Pending"),
                    ("issued", "Issued"),
                    ("partially_paid", "Partially Paid"),
                    ("paid", "Paid"),
                    ("cancelled", "Cancelled"),
                    ("overdue", "Overdue"),
                    ("refunded", "Refunded"),
                    ("void", "Void"),
                ],
                db_index=True,
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="paymentrecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("paid", "Paid"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                    ("refunded", "Refunded"),
                ],
                db_index=True,
                default="paid",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="InvoiceStatusHistory",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending"),
                            ("issued", "Issued"),
                            ("partially_paid", "Partially Paid"),
                            ("paid", "Paid"),
                            ("cancelled", "Cancelled"),
                            ("overdue", "Overdue"),
                            ("refunded", "Refunded"),
                            ("void", "Void"),
                        ],
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending"),
                            ("issued", "Issued"),
                            ("partially_paid", "Partially Paid"),
                            ("paid", "Paid"),
                            ("cancelled", "Cancelled"),
                            ("overdue", "Overdue"),
                            ("refunded", "Refunded"),
                            ("void", "Void"),
                        ],
                        max_length=20,
                    ),
                ),
                ("changed_by_id", models.UUIDField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("changed_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_history",
                        to="invoices.invoice",
                    ),
                ),
            ],
            options={
                "db_table": "billing_invoice_status_history",
                "ordering": ["-changed_at"],
            },
        ),
        migrations.CreateModel(
            name="RefundRecord",
            fields=[
                (
                    "created_by_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                ("updated_by_id", models.UUIDField(blank=True, null=True)),
                ("deleted_by_id", models.UUIDField(blank=True, null=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reason", models.TextField()),
                ("reference_number", models.CharField(blank=True, max_length=100)),
                (
                    "refunded_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("processed_by_id", models.UUIDField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refunds",
                        to="invoices.invoice",
                    ),
                ),
            ],
            options={
                "db_table": "billing_refund_record",
            },
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("is_deleted", False), ("placement_fee_id__isnull", False)
                ),
                fields=("placement_fee_id",),
                name="unique_active_invoice_per_placement_fee",
            ),
        ),
    ]
