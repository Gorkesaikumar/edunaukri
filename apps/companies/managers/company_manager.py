"""Model managers for the Company Management module."""

from apps.core.managers import ActiveManager, SoftDeleteQuerySet


class CompanyQuerySet(SoftDeleteQuerySet):
    def verified(self):
        return self

    def pending(self):
        return self.none()

    def active(self):
        return self.filter(is_active=True)

    def can_publish_jobs(self):
        """Only active companies may publish jobs."""
        return self.filter(is_active=True)


class CompanyManager(ActiveManager.from_queryset(CompanyQuerySet)):
    """Default manager returning only non-deleted companies with domain scopes."""
