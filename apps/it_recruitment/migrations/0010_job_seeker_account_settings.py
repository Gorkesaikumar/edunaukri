# Generated manually for job seeker account settings

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("it_recruitment", "0009_job_seeker_certificate_files"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobSeekerAccountSettings",
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
                ("notify_job_recommendations", models.BooleanField(default=True)),
                ("notify_recruiter_messages", models.BooleanField(default=True)),
                ("notify_application_updates", models.BooleanField(default=True)),
                ("notify_interviews", models.BooleanField(default=True)),
                ("notify_offers", models.BooleanField(default=True)),
                ("notify_marketing", models.BooleanField(default=False)),
                ("notify_security_alerts", models.BooleanField(default=True)),
                ("notify_profile_views", models.BooleanField(default=True)),
                ("notify_resume_downloads", models.BooleanField(default=True)),
                ("notify_weekly_digest", models.BooleanField(default=True)),
                ("allow_recruiter_resume_download", models.BooleanField(default=True)),
                ("allow_recruiter_contact", models.BooleanField(default=True)),
                ("show_email_on_profile", models.BooleanField(default=False)),
                ("show_phone_on_profile", models.BooleanField(default=False)),
                ("password_changed_at", models.DateTimeField(blank=True, null=True)),
                ("phone_verified", models.BooleanField(default=False)),
                (
                    "job_seeker",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="account_settings",
                        to="it_recruitment.jobseekerprofile",
                    ),
                ),
            ],
            options={
                "db_table": "it_job_seeker_account_settings",
            },
        ),
    ]
