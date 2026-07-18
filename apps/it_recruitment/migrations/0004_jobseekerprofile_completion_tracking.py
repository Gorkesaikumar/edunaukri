# Generated manually for profile completion workflow

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("it_recruitment", "0003_alter_jobseekerprofile_managers_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobseekerprofile",
            name="profile_completed",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="completion_animation_shown",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="profile_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="profile_completion_fingerprint",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
