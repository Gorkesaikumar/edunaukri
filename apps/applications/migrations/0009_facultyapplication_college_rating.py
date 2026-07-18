from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0008_job_application_interview"),
    ]

    operations = [
        migrations.AddField(
            model_name="facultyapplication",
            name="college_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
