"""Read and write persisted job recommendation cache."""

from __future__ import annotations

from django.utils import timezone

from apps.core.services.base import BaseService
from apps.it_recruitment.constants.recommendation_constants import (
    MAX_CACHED_RECOMMENDATIONS,
)
from apps.it_recruitment.models import (
    JobSeekerJobRecommendation,
    JobSeekerProfile,
    JobSeekerRecommendationSnapshot,
)
from apps.it_recruitment.services.job_matching_service import JobMatchResult
from apps.jobs.models import JobPosting


class JobRecommendationCacheService(BaseService):
    """Persist and retrieve cached recommendation rows."""

    def get_snapshot(
        self, profile: JobSeekerProfile
    ) -> JobSeekerRecommendationSnapshot | None:
        return (
            JobSeekerRecommendationSnapshot.objects.filter(job_seeker=profile)
            .select_related("top_match_job")
            .first()
        )

    def get_cached_rows(
        self,
        profile: JobSeekerProfile,
        *,
        limit: int = MAX_CACHED_RECOMMENDATIONS,
    ):
        return (
            JobSeekerJobRecommendation.objects.filter(
                job_seeker=profile,
                is_deleted=False,
            )
            .select_related(
                "job_posting", "job_posting__company", "job_posting__company__logo_file"
            )
            .prefetch_related("job_posting__required_skills__skill")
            .order_by("rank")[:limit]
        )

    def get_previous_job_ids(self, profile: JobSeekerProfile) -> set:
        return set(
            JobSeekerJobRecommendation.objects.filter(
                job_seeker=profile, is_deleted=False
            ).values_list("job_posting_id", flat=True)
        )

    @BaseService.atomic
    def persist_rebuild(
        self,
        profile: JobSeekerProfile,
        *,
        ranked: list[tuple[JobPosting, JobMatchResult]],
        fingerprint: str,
        previous_job_ids: set,
    ) -> JobSeekerRecommendationSnapshot:
        now = timezone.now()
        new_job_ids = {job.pk for job, _ in ranked}
        removed_ids = previous_job_ids - new_job_ids

        if removed_ids:
            JobSeekerJobRecommendation.objects.filter(
                job_seeker=profile,
                job_posting_id__in=removed_ids,
            ).delete()

        new_matches = 0
        for rank, (job, result) in enumerate(ranked, start=1):
            is_new = job.pk not in previous_job_ids
            if is_new:
                new_matches += 1
            JobSeekerJobRecommendation.objects.update_or_create(
                job_seeker=profile,
                job_posting=job,
                defaults={
                    "match_score": result.score,
                    "score_breakdown": result.breakdown,
                    "rank": rank,
                    "profile_fingerprint": fingerprint,
                    "computed_at": now,
                    "is_new": is_new,
                    "is_deleted": False,
                },
            )

        top_job = ranked[0][0] if ranked else None
        top_score = ranked[0][1].score if ranked else 0

        snapshot, _ = JobSeekerRecommendationSnapshot.objects.update_or_create(
            job_seeker=profile,
            defaults={
                "total_matches": len(ranked),
                "new_matches_count": new_matches,
                "top_match_score": top_score,
                "top_match_job": top_job,
                "profile_fingerprint": fingerprint,
                "computed_at": now,
            },
        )
        return snapshot

    @BaseService.atomic
    def clear_cache(self, profile: JobSeekerProfile) -> None:
        JobSeekerJobRecommendation.objects.filter(job_seeker=profile).delete()
        JobSeekerRecommendationSnapshot.objects.filter(job_seeker=profile).delete()

    @BaseService.atomic
    def upsert_single_job(
        self,
        profile: JobSeekerProfile,
        job: JobPosting,
        result: JobMatchResult,
        *,
        fingerprint: str,
        is_new: bool,
    ) -> None:
        now = timezone.now()
        JobSeekerJobRecommendation.objects.update_or_create(
            job_seeker=profile,
            job_posting=job,
            defaults={
                "match_score": result.score,
                "score_breakdown": result.breakdown,
                "profile_fingerprint": fingerprint,
                "computed_at": now,
                "is_new": is_new,
                "is_deleted": False,
            },
        )

    def recompute_ranks(self, profile: JobSeekerProfile) -> None:
        rows = list(
            JobSeekerJobRecommendation.objects.filter(
                job_seeker=profile, is_deleted=False
            )
            .select_related("job_posting")
            .order_by("-match_score", "-job_posting__published_at")
        )
        for rank, row in enumerate(rows, start=1):
            if row.rank != rank:
                row.rank = rank
                row.save(update_fields=["rank", "updated_at"])

        snapshot = self.get_snapshot(profile)
        if snapshot and rows:
            snapshot.total_matches = len(rows)
            snapshot.top_match_score = rows[0].match_score
            snapshot.top_match_job = rows[0].job_posting
            snapshot.computed_at = timezone.now()
            snapshot.save(
                update_fields=[
                    "total_matches",
                    "top_match_score",
                    "top_match_job",
                    "computed_at",
                    "updated_at",
                ]
            )
