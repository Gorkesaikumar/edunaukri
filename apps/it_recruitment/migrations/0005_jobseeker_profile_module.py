# Generated manually for job seeker profile module expansion

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("it_recruitment", "0004_jobseekerprofile_completion_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobseekerprofile",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="country",
            field=models.CharField(blank=True, default="India", max_length=100),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="gender",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="personal_website",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="preferred_roles",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="jobseekerprofile",
            name="work_mode_preference",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="cgpa",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=4, null=True
            ),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="college",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="percentage",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True
            ),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="university",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="jobseekerexperience",
            name="employment_type",
            field=models.CharField(blank=True, default="full_time", max_length=50),
        ),
        migrations.CreateModel(
            name="JobSeekerProject",
            fields=[
                (
                    "id",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created_by_id", models.UUIDField(blank=True, null=True)),
                ("updated_by_id", models.UUIDField(blank=True, null=True)),
                ("deleted_by_id", models.UUIDField(blank=True, null=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("technologies", models.JSONField(blank=True, default=list)),
                ("project_url", models.URLField(blank=True)),
                ("github_url", models.URLField(blank=True)),
                (
                    "job_seeker",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="projects",
                        to="it_recruitment.jobseekerprofile",
                    ),
                ),
            ],
            options={
                "db_table": "it_job_seeker_project",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="JobSeekerCertification",
            fields=[
                (
                    "id",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created_by_id", models.UUIDField(blank=True, null=True)),
                ("updated_by_id", models.UUIDField(blank=True, null=True)),
                ("deleted_by_id", models.UUIDField(blank=True, null=True)),
                ("name", models.CharField(max_length=300)),
                ("issuing_organization", models.CharField(blank=True, max_length=300)),
                ("issue_date", models.DateField(blank=True, null=True)),
                ("credential_id", models.CharField(blank=True, max_length=200)),
                ("credential_url", models.URLField(blank=True)),
                (
                    "job_seeker",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="certifications",
                        to="it_recruitment.jobseekerprofile",
                    ),
                ),
            ],
            options={
                "db_table": "it_job_seeker_certification",
                "ordering": ["-issue_date", "-created_at"],
            },
        ),
    ]
