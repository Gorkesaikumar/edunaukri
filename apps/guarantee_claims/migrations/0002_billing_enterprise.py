# Generated manually for billing enterprise module

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


def populate_claim_numbers(apps, schema_editor):
    GuaranteeClaim = apps.get_model("guarantee_claims", "GuaranteeClaim")
    for claim in GuaranteeClaim.objects.all():
        claim.claim_number = f"CLM-MIG-{str(claim.id).replace('-', '')[:8].upper()}"
        claim.save(update_fields=["claim_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("guarantee_claims", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlacementGuarantee",
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
                (
                    "domain",
                    models.CharField(
                        choices=[
                            ("it", "IT Recruitment"),
                            ("faculty", "Faculty Recruitment"),
                            ("platform", "Platform"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("invoice_id", models.UUIDField(db_index=True)),
                (
                    "placement_fee_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                (
                    "application_entity_type",
                    models.CharField(
                        choices=[
                            ("it_job_application", "IT Job Application"),
                            ("faculty_application", "Faculty Application"),
                            ("it_job_posting", "IT Job Posting"),
                            ("faculty_vacancy", "Faculty Vacancy"),
                            ("it_company", "IT Company"),
                            ("faculty_college", "Faculty College"),
                            ("stored_file", "Stored File"),
                        ],
                        max_length=40,
                    ),
                ),
                ("application_entity_id", models.UUIDField(db_index=True)),
                ("guarantee_days", models.PositiveIntegerField(default=90)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("expired", "Expired"),
                            ("claimed", "Claimed"),
                            ("closed", "Closed"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "db_table": "billing_placement_guarantee",
            },
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="claim_number",
            field=models.CharField(max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="approval_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="approved_by_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="exit_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="guarantee_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="resolution",
            field=models.CharField(
                blank=True,
                choices=[
                    ("fee_waiver", "Fee Waiver"),
                    ("replacement_search", "Replacement Search"),
                    ("refund", "Refund"),
                    ("rejected", "Rejected"),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="guaranteeclaim",
            name="supporting_documents",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(populate_claim_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="guaranteeclaim",
            name="claim_number",
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.CreateModel(
            name="GuaranteeClaimHistory",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("submitted", "Submitted"),
                            ("under_review", "Under Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("resolved", "Resolved"),
                        ],
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("under_review", "Under Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("resolved", "Resolved"),
                        ],
                        max_length=20,
                    ),
                ),
                ("changed_by_id", models.UUIDField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("changed_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="guarantee_claims.guaranteeclaim",
                    ),
                ),
            ],
            options={
                "db_table": "billing_guarantee_claim_history",
                "ordering": ["-changed_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="placementguarantee",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("invoice_id",),
                name="unique_active_guarantee_per_invoice",
            ),
        ),
        migrations.AddConstraint(
            model_name="guaranteeclaim",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False))
                & ~models.Q(("status__in", ["rejected", "resolved"])),
                fields=("invoice_id",),
                name="unique_active_claim_per_invoice",
            ),
        ),
    ]
