from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser


@receiver(post_save, sender=ITUser)
@receiver(post_save, sender=ProfessorUser)
@receiver(post_save, sender=CollegeUser)
def ensure_user_audit_defaults(sender, instance, created, **kwargs):
    """Hook point for future registration audit / welcome notification dispatch."""
    if created:
        return
