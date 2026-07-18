"""Domain signals for the Job Management module."""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from apps.jobs.models import JobPosting


@receiver(pre_save, sender=JobPosting)
def ensure_job_slug(sender, instance: JobPosting, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)[:350]


@receiver(pre_save, sender=JobPosting)
def ensure_company_name_snapshot(sender, instance: JobPosting, **kwargs):
    if not instance.company_name_snapshot and instance.company_id:
        instance.company_name_snapshot = instance.company.name


@receiver(pre_save, sender=JobPosting)
def ensure_job_code(sender, instance: JobPosting, **kwargs):
    """Derive a stable job code from the primary key when one is not supplied."""
    if not instance.job_code and instance.pk:
        instance.job_code = f"JOB-{str(instance.pk).split('-')[0].upper()}"
