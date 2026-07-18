import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db.models import Value, CharField
from apps.jobs.models import JobPosting
from apps.faculty.models import FacultyVacancy
from apps.jobs.constants.enums import JobStatus, JobVisibility
from apps.faculty.constants.enums import VacancyStatus, VacancyVisibility


def test_union():
    it_qs = (
        JobPosting.objects.filter(
            status=JobStatus.PUBLISHED, visibility=JobVisibility.PUBLIC
        )
        .annotate(domain=Value("it", output_field=CharField(max_length=10)))
        .values("id", "domain", "title", "published_at", "created_at")
    )

    fac_qs = (
        FacultyVacancy.objects.filter(
            status=VacancyStatus.PUBLISHED, visibility=VacancyVisibility.PUBLIC
        )
        .annotate(domain=Value("faculty", output_field=CharField(max_length=10)))
        .values("id", "domain", "title", "published_at", "created_at")
    )

    unified = it_qs.union(fac_qs).order_by("-published_at")
    print("Total items:", unified.count())
    for item in unified[:5]:
        print(item)


if __name__ == "__main__":
    test_union()
