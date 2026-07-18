"""Recruiter account settings model."""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "it_recruitment",
            "0011_rename_it_cert_seeker_cat_idx_it_job_seek_job_see_6ad116_idx_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="RecruiterAccountSettings",
            fields=[
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
                ("created_by_id", models.UUIDField(blank=True, null=True)),
                ("updated_by_id", models.UUIDField(blank=True, null=True)),
                ("deleted_by_id", models.UUIDField(blank=True, null=True)),
                ("notify_new_applications", models.BooleanField(default=True)),
                ("notify_interview_updates", models.BooleanField(default=True)),
                ("notify_candidate_messages", models.BooleanField(default=True)),
                ("notify_marketing", models.BooleanField(default=False)),
                ("notify_security_alerts", models.BooleanField(default=True)),
                ("password_changed_at", models.DateTimeField(blank=True, null=True)),
                ("phone_verified", models.BooleanField(default=False)),
                (
                    "recruiter",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="account_settings",
                        to="it_recruitment.recruiterprofile",
                    ),
                ),
            ],
            options={
                "db_table": "it_recruiter_account_settings",
            },
        ),
    ]
