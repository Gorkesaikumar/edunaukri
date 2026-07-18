from apps.accounts.profiles.constants.enums import ProfileStatus, ProfileVisibility
from apps.core.managers.soft_delete import ActiveManager, SoftDeleteQuerySet


class ProfileQuerySet(SoftDeleteQuerySet):
    """Query helpers for lifecycle and visibility on profile entities."""

    def with_active_status(self):
        return self.filter(profile_status=ProfileStatus.ACTIVE)

    def deactivated(self):
        return self.filter(profile_status=ProfileStatus.DEACTIVATED)

    def publicly_visible(self):
        return self.with_active_status().filter(
            profile_visibility=ProfileVisibility.PUBLIC
        )


class ProfileManager(ActiveManager.from_queryset(ProfileQuerySet)):
    """Default read manager for profile entities (non-deleted rows)."""


class PublicProfileManager(ProfileManager):
    """Active, non-deleted profiles eligible for anonymous discovery."""

    def get_queryset(self):
        return super().get_queryset().publicly_visible()
