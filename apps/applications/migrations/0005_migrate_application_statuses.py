from django.db import migrations

STATUS_MAP = {
    "submitted": "applied",
    "interview": "interview_scheduled",
    "offered": "offer_released",
    "placed": "hired",
}


def migrate_status_values(apps, schema_editor):
    JobApplication = apps.get_model("applications", "JobApplication")
    JobApplicationStatusHistory = apps.get_model(
        "applications", "JobApplicationStatusHistory"
    )

    for old, new in STATUS_MAP.items():
        JobApplication.objects.filter(status=old).update(status=new)
        JobApplicationStatusHistory.objects.filter(from_status=old).update(
            from_status=new
        )
        JobApplicationStatusHistory.objects.filter(to_status=old).update(to_status=new)

    JobPosting = apps.get_model("jobs", "JobPosting")
    for application in JobApplication.objects.filter(
        company_id__isnull=True
    ).iterator():
        job = JobPosting.objects.filter(pk=application.job_posting_id).first()
        if job:
            JobApplication.objects.filter(pk=application.pk).update(
                company_id=job.company_id,
                company_name_snapshot=job.company_name_snapshot,
            )
        if (
            application.status == "hired"
            and application.placed_at
            and not application.hired_at
        ):
            JobApplication.objects.filter(pk=application.pk).update(
                hired_at=application.placed_at
            )


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0004_jobapplicationtimelineevent_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_status_values, migrations.RunPython.noop),
    ]
