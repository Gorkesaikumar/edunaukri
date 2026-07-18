"""Model managers for the College / Institution Management module."""

from apps.core.managers import ActiveManager, SoftDeleteQuerySet


class InstitutionQuerySet(SoftDeleteQuerySet):
    def verified(self):
        return self

    def pending(self):
        return self.none()

    def active(self):
        return self.filter(is_active=True)

    def can_publish_vacancies(self):
        """Only active institutions can publish faculty vacancies."""
        return self.filter(is_active=True)


class InstitutionManager(ActiveManager.from_queryset(InstitutionQuerySet)):
    """Default manager returning only non-deleted institutions with domain scopes."""
