from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("it_recruitment", "0006_alter_jobseekercertification_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobseekereducation",
            name="board",
            field=models.CharField(
                blank=True,
                choices=[
                    ("cbse", "CBSE"),
                    ("icse", "ICSE"),
                    ("state_board", "State Board"),
                    ("other", "Others"),
                ],
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="degree_type",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="education_level",
            field=models.CharField(
                choices=[
                    ("school", "School (SSC / 10th)"),
                    ("intermediate", "Intermediate (12th / Diploma)"),
                    ("degree", "Degree / B.Tech"),
                    ("post_graduation", "Post Graduation"),
                ],
                db_index=True,
                default="degree",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="passing_year",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="score_type",
            field=models.CharField(
                blank=True,
                choices=[("percentage", "Percentage"), ("cgpa", "CGPA")],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="jobseekereducation",
            name="stream",
            field=models.CharField(
                blank=True,
                choices=[
                    ("mpc", "MPC"),
                    ("bipc", "BiPC"),
                    ("mec", "MEC"),
                    ("cec", "CEC"),
                    ("diploma", "Diploma"),
                    ("other", "Others"),
                ],
                max_length=50,
            ),
        ),
        migrations.AlterModelOptions(
            name="jobseekereducation",
            options={
                "ordering": [
                    "education_level",
                    "-end_year",
                    "-passing_year",
                    "-start_year",
                ],
            },
        ),
    ]
