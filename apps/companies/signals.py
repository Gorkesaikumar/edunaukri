"""Domain signals for the Company Management module.

Connected in ``CompaniesConfig.ready()``. Keeps derived state consistent
(slug generation as a safety net, and de-duplication of a single primary
company member) without embedding business logic in the ORM layer.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from apps.companies.models import Company, CompanyMember


@receiver(pre_save, sender=Company)
def ensure_company_slug(sender, instance: Company, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)[:320]


@receiver(pre_save, sender=CompanyMember)
def ensure_single_primary_member(sender, instance: CompanyMember, **kwargs):
    if not instance.is_primary or not instance.company_id:
        return
    (
        CompanyMember.objects.filter(company_id=instance.company_id, is_primary=True)
        .exclude(pk=instance.pk)
        .update(is_primary=False)
    )
