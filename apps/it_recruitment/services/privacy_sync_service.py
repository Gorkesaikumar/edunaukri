"""Invalidate caches and refresh derived data after privacy changes."""

from __future__ import annotations

from django.core.cache import cache

from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)


class PrivacySyncService(BaseService):
    """Refresh search visibility and cached profile data after privacy updates."""

    CACHE_KEY_PREFIX = "it:jobseeker:privacy:"

    def on_privacy_changed(
        self, profile: JobSeekerProfile, changed_fields: list[str]
    ) -> None:
        self.invalidate_profile_cache(profile)
        if "profile_visibility" in changed_fields:
            self._refresh_search_visibility(profile)

    def invalidate_profile_cache(self, profile: JobSeekerProfile) -> None:
        cache.delete(f"{self.CACHE_KEY_PREFIX}{profile.pk}")
        cache.delete(f"{self.CACHE_KEY_PREFIX}user:{profile.user_id}")

    def _refresh_search_visibility(self, profile: JobSeekerProfile) -> None:
        from apps.accounts.profiles.constants.enums import ProfileVisibility

        if profile.profile_visibility == ProfileVisibility.PRIVATE:
            JobRecommendationCacheService().clear_cache(profile)
