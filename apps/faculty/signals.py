"""Domain signals for the Faculty Vacancy Management module."""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from apps.faculty.models import FacultyVacancy


@receiver(pre_save, sender=FacultyVacancy)
def ensure_vacancy_slug(sender, instance: FacultyVacancy, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)[:350]


@receiver(pre_save, sender=FacultyVacancy)
def ensure_college_name_snapshot(sender, instance: FacultyVacancy, **kwargs):
    if not instance.college_name_snapshot and instance.college_id:
        instance.college_name_snapshot = instance.college.name


@receiver(pre_save, sender=FacultyVacancy)
def ensure_vacancy_code(sender, instance: FacultyVacancy, **kwargs):
    """Derive a stable vacancy code from the primary key when one is not supplied."""
    if not instance.vacancy_code and instance.pk:
        instance.vacancy_code = f"VAC-{str(instance.pk).split('-')[0].upper()}"
