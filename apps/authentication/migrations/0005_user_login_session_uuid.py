"""Add permanent session UUID to login session records."""

import uuid

from django.db import migrations, models


def assign_session_uuids(apps, schema_editor):
    UserLoginSession = apps.get_model("authentication", "UserLoginSession")
    for session in UserLoginSession.objects.all().only("pk"):
        UserLoginSession.objects.filter(pk=session.pk).update(session_uuid=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0004_user_security_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="userloginsession",
            name="session_uuid",
            field=models.UUIDField(db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(assign_session_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userloginsession",
            name="session_uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
