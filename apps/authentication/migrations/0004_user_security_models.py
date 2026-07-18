# Generated manually for user security models

import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0003_session_revocation"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLoginSession",
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
                ("domain", models.CharField(db_index=True, max_length=20)),
                ("user_id", models.UUIDField(db_index=True)),
                (
                    "session_key",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("device_label", models.CharField(blank=True, max_length=200)),
                ("browser", models.CharField(blank=True, max_length=80)),
                ("os_name", models.CharField(blank=True, max_length=80)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("location_label", models.CharField(blank=True, max_length=120)),
                (
                    "login_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                (
                    "last_active_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "auth_user_login_session",
                "ordering": ["-last_active_at"],
            },
        ),
        migrations.CreateModel(
            name="SecurityAuditEvent",
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
                ("domain", models.CharField(db_index=True, max_length=20)),
                ("user_id", models.UUIDField(db_index=True)),
                ("event_type", models.CharField(db_index=True, max_length=60)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "occurred_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
            ],
            options={
                "db_table": "auth_security_audit_event",
                "ordering": ["-occurred_at"],
            },
        ),
        migrations.CreateModel(
            name="ConnectedOAuthAccount",
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
                ("domain", models.CharField(db_index=True, max_length=20)),
                ("user_id", models.UUIDField(db_index=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("google", "Google"), ("linkedin", "LinkedIn")],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("provider_user_id", models.CharField(blank=True, max_length=200)),
                ("provider_email", models.EmailField(blank=True, max_length=254)),
                ("connected_at", models.DateTimeField(blank=True, null=True)),
                ("disconnected_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "auth_connected_oauth_account",
            },
        ),
        migrations.AddIndex(
            model_name="userloginsession",
            index=models.Index(
                fields=["domain", "user_id", "-last_active_at"],
                name="auth_session_user_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="securityauditevent",
            index=models.Index(
                fields=["domain", "user_id", "-occurred_at"], name="auth_audit_user_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="connectedoauthaccount",
            constraint=models.UniqueConstraint(
                fields=("domain", "user_id", "provider"),
                name="auth_oauth_unique_provider_per_user",
            ),
        ),
    ]
