# Generated manually for billing enterprise module

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="feeschedule",
            name="scope_type",
            field=models.CharField(
                choices=[
                    ("global", "Global"),
                    ("recruiter", "Recruiter"),
                    ("college", "College"),
                    ("role", "Role"),
                    ("designation", "Designation"),
                ],
                db_index=True,
                default="global",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="feeschedule",
            name="scope_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
