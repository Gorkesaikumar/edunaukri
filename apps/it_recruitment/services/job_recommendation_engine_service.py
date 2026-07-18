"""Enterprise job recommendation engine — compute, cache, and notify."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.core.services.base import BaseService
from apps.it_recruitment.constants.recommendation_constants import (
    API_RECOMMENDATION_LIMIT,
    MIN_MATCH_SCORE,
    MAX_CACHED_RECOMMENDATIONS,
)
from apps.it_recruitment.models import JobSeekerJobRecommendation, JobSeekerProfile
from apps.it_recruitment.services.job_matching_service import JobMatchingService
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.job_recommendation_notification_service import (
    JobRecommendationNotificationService,
)
from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
    JobSeekerResumeAnalysisService,
)
from apps.it_recruitment.services.recommendation_fingerprint_service import (
    compute_profile_fingerprint,
)
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting, SavedJob


@dataclass
class RecommendationSummary:
    total_matches: int
    new_matches_count: int
    top_match_score: int
    top_match_title: str | None
    computed_at: str | None
    unread_notification_count: int = 0
    jobs: list[dict] | None = None

    def to_dict(self) -> dict:
        payload = {
            "total_matches": self.total_matches,
            "new_matches_count": self.new_matches_count,
            "top_match_score": self.top_match_score,
            "top_match_title": self.top_match_title,
            "computed_at": self.computed_at,
            "unread_notification_count": self.unread_notification_count,
        }
        if self.jobs is not None:
            payload["jobs"] = self.jobs
        return payload


class JobRecommendationEngineService(BaseService):
    """Orchestrate matching, caching, and notifications for job seekers."""

    def __init__(self):
        self.matcher = JobMatchingService()
        self.cache = JobRecommendationCacheService()
        self.notifications = JobRecommendationNotificationService()
        self.resume_analysis = JobSeekerResumeAnalysisService()

    def rebuild_for_seeker(
        self,
        profile_id,
        *,
        reason: str = "profile_update",
        notify: bool = True,
        include_jobs: bool = False,
        job_limit: int = API_RECOMMENDATION_LIMIT,
    ) -> RecommendationSummary:
        profile = self._load_profile(profile_id)
        fingerprint = compute_profile_fingerprint(profile)
        previous_job_ids = self.cache.get_previous_job_ids(profile)

        jobs = self._eligible_jobs(profile)
        analysis = self.resume_analysis.get_analysis(profile)
        behavioral = self._behavioral_boosts(profile)

        seeker_skill_ids = set(
            profile.skills.filter(is_deleted=False).values_list("skill_id", flat=True)
        )
        scored: list = []
        for job in jobs:
            result = self.matcher.score_job(
                profile,
                job,
                analysis=analysis,
                seeker_skill_ids=seeker_skill_ids,
                behavioral_boost=behavioral.get(job.pk, 0),
            )
            if result.score >= MIN_MATCH_SCORE:
                scored.append((job, result))

        scored.sort(
            key=lambda item: (
                item[1].score,
                item[0].is_featured,
                item[0].published_at or item[0].created_at,
            ),
            reverse=True,
        )
        ranked = scored[:MAX_CACHED_RECOMMENDATIONS]

        snapshot = self.cache.persist_rebuild(
            profile,
            ranked=ranked,
            fingerprint=fingerprint,
            previous_job_ids=previous_job_ids,
        )

        if notify and snapshot.new_matches_count > 0:
            top_pairs = [(job, result.score) for job, result in ranked[:5]]
            self.notifications.notify_preference_rebuild(
                profile, snapshot, top_jobs=top_pairs
            )
            self.notifications.deliver_pending_notifications()

        return self._build_summary(
            profile,
            snapshot,
            ranked[:job_limit] if include_jobs else None,
            from_cache=False,
        )

    def score_job_for_all_seekers(self, job_id, *, notify: bool = True) -> int:
        """When a new job is published, score it against active seekers."""
        job = (
            JobPosting.objects.filter(pk=job_id, is_deleted=False)
            .prefetch_related("required_skills__skill")
            .select_related("company")
            .first()
        )
        if not job or job.status != JobStatus.PUBLISHED:
            return 0

        updated = 0
        seekers = JobSeekerProfile.objects.filter(
            is_deleted=False,
            profile_status="active",
        ).iterator(chunk_size=50)

        for profile in seekers:
            if self._seeker_excluded_from_job(profile, job):
                continue
            fingerprint = compute_profile_fingerprint(profile)
            analysis = self.resume_analysis.get_analysis(profile)
            behavioral = self._behavioral_boosts(profile)
            result = self.matcher.score_job(
                profile,
                job,
                analysis=analysis,
                behavioral_boost=behavioral.get(job.pk, 0),
            )
            if result.score < MIN_MATCH_SCORE:
                JobSeekerJobRecommendation.objects.filter(
                    job_seeker=profile,
                    job_posting=job,
                ).delete()
                continue

            previous = self.cache.get_previous_job_ids(profile)
            is_new = job.pk not in previous
            self.cache.upsert_single_job(
                profile,
                job,
                result,
                fingerprint=fingerprint,
                is_new=is_new,
            )
            self.cache.recompute_ranks(profile)

            if notify and is_new:
                self.notifications.notify_single_job_match(
                    profile, job, match_score=result.score
                )
            updated += 1

        if notify and updated:
            self.notifications.deliver_pending_notifications(limit=50)
        return updated

    def get_recommendations(
        self,
        profile: JobSeekerProfile,
        *,
        limit: int = API_RECOMMENDATION_LIMIT,
        force_rebuild: bool = False,
    ) -> RecommendationSummary:
        snapshot = self.cache.get_snapshot(profile)
        if force_rebuild or snapshot is None:
            return self.rebuild_for_seeker(
                profile.pk,
                reason="api_refresh",
                notify=False,
                include_jobs=True,
                job_limit=limit,
            )

        fingerprint = compute_profile_fingerprint(profile)
        if snapshot.profile_fingerprint != fingerprint:
            return self.rebuild_for_seeker(
                profile.pk,
                reason="cache_stale",
                notify=False,
                include_jobs=True,
                job_limit=limit,
            )

        rows = self.cache.get_cached_rows(profile, limit=limit)
        ranked = [(row.job_posting, row) for row in rows]
        return self._build_summary(profile, snapshot, ranked, from_cache=True)

    def serialize_job_cards(
        self,
        profile: JobSeekerProfile,
        ranked,
        *,
        from_cache: bool = False,
    ) -> list[dict]:
        from apps.authentication.services.portal_url_service import PortalURLService

        user = profile.user
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        saved_ids = set(
            SavedJob.objects.filter(job_seeker=profile, is_deleted=False).values_list(
                "job_posting_id", flat=True
            )
        )
        cards = []
        for item in ranked:
            if from_cache:
                job, row = item
                score = row.match_score
                is_new = row.is_new
            else:
                job, result = item
                score = result.score
                is_new = False
            tags = []
            if job.employment_type:
                tags.append(job.get_employment_type_display())
            if job.work_mode:
                tags.append(job.get_work_mode_display())
            cards.append(
                {
                    "id": str(job.pk),
                    "title": job.title,
                    "company_name": job.company_name_snapshot
                    or (job.company.name if job.company_id else ""),
                    "match_percent": score,
                    "tags": tags[:2],
                    "detail_url": pu("jobseeker_job_detail", job_id=job.pk),
                    "apply_url": pu("jobseeker_job_apply", job_id=job.pk),
                    "save_url": pu("jobseeker_save_job", job_id=job.pk),
                    "is_saved": job.pk in saved_ids,
                    "is_new": is_new,
                }
            )
        return cards

    def _build_summary(
        self,
        profile: JobSeekerProfile,
        snapshot,
        ranked,
        *,
        from_cache: bool = False,
    ) -> RecommendationSummary:
        from apps.notifications.models import Notification

        top_title = None
        if snapshot.top_match_job_id:
            top_title = snapshot.top_match_job.title if snapshot.top_match_job else None

        jobs = None
        if ranked is not None:
            jobs = self.serialize_job_cards(profile, ranked, from_cache=from_cache)

        unread = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            is_read=False,
        ).count()

        computed = snapshot.computed_at.isoformat() if snapshot.computed_at else None
        return RecommendationSummary(
            total_matches=snapshot.total_matches,
            new_matches_count=snapshot.new_matches_count,
            top_match_score=snapshot.top_match_score,
            top_match_title=top_title,
            computed_at=computed,
            unread_notification_count=unread,
            jobs=jobs,
        )

    def _eligible_jobs(self, profile: JobSeekerProfile):
        now = timezone.now()
        applied_ids = set(
            JobApplication.objects.filter(
                job_seeker=profile, is_deleted=False
            ).values_list("job_posting_id", flat=True)
        )
        rejected_ids = set(
            JobApplication.objects.filter(
                job_seeker=profile,
                is_deleted=False,
                status=JobApplicationStatus.REJECTED,
            ).values_list("job_posting_id", flat=True)
        )
        exclude_ids = applied_ids | rejected_ids

        return (
            JobPosting.objects.filter(status=JobStatus.PUBLISHED, is_deleted=False)
            .exclude(pk__in=exclude_ids)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .select_related("company", "company__logo_file")
            .prefetch_related("required_skills__skill")
        )

    @staticmethod
    def _seeker_excluded_from_job(profile: JobSeekerProfile, job: JobPosting) -> bool:
        if JobApplication.objects.filter(
            job_seeker=profile,
            job_posting=job,
            is_deleted=False,
        ).exists():
            return True
        now = timezone.now()
        if job.expires_at and job.expires_at <= now:
            return True
        return job.status != JobStatus.PUBLISHED

    @staticmethod
    def _behavioral_boosts(profile: JobSeekerProfile) -> dict:
        """Light personalization from saved jobs and application history."""
        boosts: dict = {}
        saved_job_ids = SavedJob.objects.filter(
            job_seeker=profile, is_deleted=False
        ).values_list("job_posting_id", flat=True)
        for job_id in saved_job_ids:
            boosts[job_id] = boosts.get(job_id, 0) + 3

        shortlisted = JobApplication.objects.filter(
            job_seeker=profile,
            is_deleted=False,
            status__in=[
                JobApplicationStatus.SHORTLISTED,
                JobApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplicationStatus.OFFER_RELEASED,
            ],
        ).values_list("job_posting_id", flat=True)
        for job_id in shortlisted:
            boosts[job_id] = boosts.get(job_id, 0) + 2
        return boosts

    @staticmethod
    def _load_profile(profile_id) -> JobSeekerProfile:
        from apps.it_recruitment.services.jobseeker_profile_manage_service import (
            PROFILE_PREFETCH,
            PROFILE_SELECT_RELATED,
        )

        profile = (
            JobSeekerProfile.objects.filter(pk=profile_id, is_deleted=False)
            .select_related(*PROFILE_SELECT_RELATED)
            .prefetch_related(*PROFILE_PREFETCH)
            .first()
        )
        if profile is None:
            from apps.core.exceptions.domain_exceptions import ResourceNotFoundException

            raise ResourceNotFoundException("Profile not found.")
        return profile
