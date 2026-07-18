"""Domain signals for the College / Institution Management module."""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from apps.colleges.models import College, CollegeMember


@receiver(pre_save, sender=College)
def ensure_college_slug(sender, instance: College, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)[:320]


@receiver(pre_save, sender=CollegeMember)
def ensure_single_primary_member(sender, instance: CollegeMember, **kwargs):
    """Guarantee at most one primary member per institution."""
    if instance.is_primary and instance.college_id:
        (
            CollegeMember.objects.filter(
                college_id=instance.college_id, is_primary=True
            )
            .exclude(pk=instance.pk)
            .update(is_primary=False)
        )
