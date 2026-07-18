from django.db import migrations

STATUS_MAP = {
    "submitted": "applied",
    "shortlisted": "department_review",
    "interview": "interview_scheduled",
    "offered": "offer_released",
    "placed": "joined",
}


def migrate_faculty_status_values(apps, schema_editor):
    FacultyApplication = apps.get_model("applications", "FacultyApplication")
    FacultyApplicationStatusHistory = apps.get_model(
        "applications", "FacultyApplicationStatusHistory"
    )
    FacultyApplicationTimelineEvent = apps.get_model(
        "applications", "FacultyApplicationTimelineEvent"
    )

    for old, new in STATUS_MAP.items():
        FacultyApplication.objects.filter(status=old).update(status=new)
        FacultyApplicationStatusHistory.objects.filter(from_status=old).update(
            from_status=new
        )
        FacultyApplicationStatusHistory.objects.filter(to_status=old).update(
            to_status=new
        )
        FacultyApplicationTimelineEvent.objects.filter(from_status=old).update(
            from_status=new
        )
        FacultyApplicationTimelineEvent.objects.filter(to_status=old).update(
            to_status=new
        )

    FacultyVacancy = apps.get_model("faculty", "FacultyVacancy")
    for application in FacultyApplication.objects.filter(
        college_id__isnull=True
    ).iterator():
        vacancy = FacultyVacancy.objects.filter(pk=application.vacancy_id).first()
        if vacancy:
            FacultyApplication.objects.filter(pk=application.pk).update(
                college_id=vacancy.college_id,
                college_name_snapshot=vacancy.college_name_snapshot,
                department=vacancy.department or "",
            )
        if (
            application.status == "joined"
            and application.placed_at
            and not application.joined_at
        ):
            FacultyApplication.objects.filter(pk=application.pk).update(
                joined_at=application.placed_at
            )


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0006_faculty_application_enterprise"),
    ]

    operations = [
        migrations.RunPython(migrate_faculty_status_values, migrations.RunPython.noop),
    ]
