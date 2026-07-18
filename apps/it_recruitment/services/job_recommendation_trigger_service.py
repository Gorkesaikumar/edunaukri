"""Schedule recommendation rebuilds synchronously or via Celery."""

from __future__ import annotations

import logging

from apps.core.services.base import BaseService

logger = logging.getLogger(__name__)

RECOMMENDATION_PROFILE_SECTIONS = frozenset(
    {"career", "skills", "header", "summary", "basic"}
)


class JobRecommendationTriggerService(BaseService):
    """Enqueue or run recommendation engine updates."""

    def schedule_seeker_rebuild(
        self,
        profile_id,
        *,
        reason: str = "profile_update",
        sync: bool = False,
        notify: bool = True,
    ) -> None:
        if sync:
            from apps.it_recruitment.services.job_recommendation_engine_service import (
                JobRecommendationEngineService,
            )

            JobRecommendationEngineService().rebuild_for_seeker(
                profile_id,
                reason=reason,
                notify=notify,
            )
            return

        try:
            from apps.it_recruitment.tasks import rebuild_seeker_recommendations_task

            rebuild_seeker_recommendations_task.delay(str(profile_id), reason, notify)
        except Exception as exc:
            logger.warning(
                "Celery unavailable for seeker rebuild (%s); running synchronously.",
                exc,
            )
            from apps.it_recruitment.services.job_recommendation_engine_service import (
                JobRecommendationEngineService,
            )

            JobRecommendationEngineService().rebuild_for_seeker(
                profile_id,
                reason=reason,
                notify=notify,
            )

    def schedule_job_rebuild(self, job_id, *, reason: str = "job_published") -> None:
        try:
            from apps.it_recruitment.tasks import rebuild_recommendations_for_job_task

            rebuild_recommendations_for_job_task.delay(str(job_id), reason)
        except Exception as exc:
            logger.warning(
                "Celery unavailable for job rebuild (%s); running synchronously.",
                exc,
            )
            from apps.it_recruitment.services.job_recommendation_engine_service import (
                JobRecommendationEngineService,
            )

            JobRecommendationEngineService().score_job_for_all_seekers(
                job_id, notify=True
            )

    @classmethod
    def after_profile_section(cls, profile_id, section: str) -> None:
        if section not in RECOMMENDATION_PROFILE_SECTIONS:
            return
        sync = section == "career"
        cls().schedule_seeker_rebuild(
            profile_id,
            reason=f"section:{section}",
            sync=sync,
            notify=sync,
        )

    @classmethod
    def after_profile_mutation(cls, profile_id, *, reason: str) -> None:
        cls().schedule_seeker_rebuild(
            profile_id, reason=reason, sync=False, notify=False
        )
