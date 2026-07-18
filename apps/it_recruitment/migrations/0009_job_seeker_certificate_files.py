# Generated manually for certificate management module

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0002_alter_storedfile_file_type"),
        ("it_recruitment", "0008_job_recommendation_cache"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobseekercertification",
            name="category",
            field=models.CharField(db_index=True, default="other", max_length=30),
        ),
        migrations.AddField(
            model_name="jobseekercertification",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobseekercertification",
            name="is_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="jobseekercertification",
            name="certificate_file",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="job_seeker_certifications",
                to="documents.storedfile",
            ),
        ),
        migrations.AddIndex(
            model_name="jobseekercertification",
            index=models.Index(
                fields=["job_seeker", "category"], name="it_cert_seeker_cat_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="jobseekercertification",
            index=models.Index(
                fields=["expiry_date"],
                name="it_cert_expiry_idx",
            ),
        ),
    ]
