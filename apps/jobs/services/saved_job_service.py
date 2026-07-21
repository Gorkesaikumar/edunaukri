"""Saved jobs — save, remove, list, and status checks for job seekers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_matching_service import JobMatchingService
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    media_url,
)
from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
    JobSeekerResumeAnalysisService,
)
from apps.jobs.constants.enums import JobStatus, JobVisibility
from apps.jobs.models import JobPosting, SavedJob
from apps.reports.selectors.featured_jobs import FeaturedJobsSelector


@dataclass
class SavedJobCard:
    id: str
    saved_id: str
    title: str
    company_name: str
    company_verified: bool
    logo_url: str | None
    logo_initial: str
    location: str
    salary_display: str | None
    experience_label: str | None
    employment_type_label: str
    work_mode_label: str
    skills: list[str]
    match_percent: int | None
    posted_display: str
    deadline_display: str | None
    is_open: bool
    detail_url: str
    apply_url: str
    save_url: str
    saved_at_display: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "saved_id": self.saved_id,
            "title": self.title,
            "company_name": self.company_name,
            "company_verified": self.company_verified,
            "logo_url": self.logo_url,
            "logo_initial": self.logo_initial,
            "location": self.location,
            "salary_display": self.salary_display,
            "experience_label": self.experience_label,
            "employment_type_label": self.employment_type_label,
            "work_mode_label": self.work_mode_label,
            "skills": self.skills,
            "match_percent": self.match_percent,
            "posted_display": self.posted_display,
            "deadline_display": self.deadline_display,
            "is_open": self.is_open,
            "detail_url": self.detail_url,
            "apply_url": self.apply_url,
            "save_url": self.save_url,
            "saved_at_display": self.saved_at_display,
            "is_saved": True,
        }


@dataclass
class SavedJobToggleResult:
    job_id: str
    is_saved: bool
    saved_count: int
    message: str

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "is_saved": self.is_saved,
            "saved_count": self.saved_count,
            "message": self.message,
        }


@dataclass
class SavedJobListResult:
    jobs: list[SavedJobCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    def to_dict(self) -> dict:
        return {
            "jobs": [job.to_dict() for job in self.jobs],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


class SavedJobService(BaseService):
    """Enterprise saved-jobs workflow with duplicate prevention."""

    def toggle(self, profile: JobSeekerProfile, job_id) -> SavedJobToggleResult:
        job = JobPosting.objects.filter(pk=job_id, is_deleted=False).first()
        if not job:
            raise ValueError("Job not found.")

        existing = SavedJob.all_objects.filter(job_seeker=profile, job_posting=job).first()
        if existing and not existing.is_deleted:
            existing.delete()
            return SavedJobToggleResult(
                job_id=str(job.pk),
                is_saved=False,
                saved_count=self.count(profile),
                message="Job removed from saved jobs.",
            )

        if existing and existing.is_deleted:
            existing.restore()
        else:
            from django.db import IntegrityError, transaction
            try:
                with transaction.atomic():
                    SavedJob.objects.create(job_seeker=profile, job_posting=job)
            except IntegrityError:
                pass

        return SavedJobToggleResult(
            job_id=str(job.pk),
            is_saved=True,
            saved_count=self.count(profile),
            message="Job saved successfully.",
        )

    @transaction.atomic
    def save(self, profile: JobSeekerProfile, job_id) -> SavedJobToggleResult:
        job = JobPosting.objects.filter(pk=job_id, is_deleted=False).first()
        if not job:
            raise ValueError("Job not found.")

        existing = SavedJob.all_objects.filter(job_seeker=profile, job_posting=job).first()
        if existing and not existing.is_deleted:
            return SavedJobToggleResult(
                job_id=str(job.pk),
                is_saved=True,
                saved_count=self.count(profile),
                message="Job saved successfully.",
            )
        if existing and existing.is_deleted:
            existing.restore()
        else:
            from django.db import IntegrityError
            try:
                with transaction.atomic():
                    SavedJob.objects.create(job_seeker=profile, job_posting=job)
            except IntegrityError:
                pass

        return SavedJobToggleResult(
            job_id=str(job.pk),
            is_saved=True,
            saved_count=self.count(profile),
            message="Job saved successfully.",
        )

    def remove(self, profile: JobSeekerProfile, job_id) -> SavedJobToggleResult:
        saved = SavedJob.objects.filter(
            job_seeker=profile,
            job_posting_id=job_id,
            is_deleted=False,
        ).first()
        if not saved:
            return SavedJobToggleResult(
                job_id=str(job_id),
                is_saved=False,
                saved_count=self.count(profile),
                message="Job removed from saved jobs.",
            )
        saved.delete()
        return SavedJobToggleResult(
            job_id=str(job_id),
            is_saved=False,
            saved_count=self.count(profile),
            message="Job removed from saved jobs.",
        )

    def count(self, profile: JobSeekerProfile) -> int:
        return SavedJob.objects.filter(job_seeker=profile, is_deleted=False).count()

    def saved_job_ids(self, profile: JobSeekerProfile) -> set:
        return set(
            SavedJob.objects.filter(job_seeker=profile, is_deleted=False).values_list(
                "job_posting_id", flat=True
            )
        )

    def status_map(self, profile: JobSeekerProfile, job_ids: list) -> dict[str, bool]:
        if not job_ids:
            return {}
        saved = set(
            SavedJob.objects.filter(
                job_seeker=profile,
                job_posting_id__in=job_ids,
                is_deleted=False,
            ).values_list("job_posting_id", flat=True)
        )
        return {str(job_id): job_id in saved for job_id in job_ids}

    def list_saved(
        self,
        profile: JobSeekerProfile,
        *,
        page: int = 1,
        page_size: int = 12,
    ) -> SavedJobListResult:
        qs = (
            SavedJob.objects.filter(job_seeker=profile, is_deleted=False)
            .select_related(
                "job_posting",
                "job_posting__company",
                "job_posting__company__logo_file",
            )
            .prefetch_related("job_posting__required_skills__skill")
            .order_by("-created_at")
        )
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        match_scores = self._match_scores(
            profile, [row.job_posting for row in page_obj.object_list]
        )
        cards = [
            self._map_card(
                row, profile, match_percent=match_scores.get(row.job_posting_id)
            )
            for row in page_obj.object_list
        ]
        return SavedJobListResult(
            jobs=cards,
            total_count=paginator.count,
            page=page_obj.number,
            page_size=page_size,
            total_pages=paginator.num_pages,
        )

    def _match_scores(self, profile: JobSeekerProfile, jobs: list[JobPosting]) -> dict:
        if not jobs:
            return {}
        cache = JobRecommendationCacheService()
        cached = {
            row.job_posting_id: row.match_score
            for row in cache.get_cached_rows(profile, limit=100)
        }
        missing = [job for job in jobs if job.pk not in cached]
        if missing:
            analysis = JobSeekerResumeAnalysisService().get_analysis(profile)
            matcher = JobMatchingService()
            for job in missing:
                cached[job.pk] = matcher.score_job(
                    profile, job, analysis=analysis
                ).score
        return cached

    def _map_card(
        self,
        saved: SavedJob,
        profile: JobSeekerProfile,
        *,
        match_percent: int | None = None,
    ) -> SavedJobCard:
        job = saved.job_posting
        mapper = FeaturedJobsSelector()
        company = job.company if job.company_id else None
        org_name = job.company_name_snapshot or (company.name if company else "")
        location = mapper._location(
            city=job.city, state=job.state, remote=job.is_remote, fallback=job.location
        )
        skills = [
            rs.skill.name
            for rs in job.required_skills.all()
            if rs.skill_id and not rs.is_deleted
        ][:6]
        detail_url = reverse("marketplace_job_detail", kwargs={"job_id": job.pk})
        apply_url = reverse("marketplace_job_apply", kwargs={"job_id": job.pk})
        pu = lambda name, **kw: PortalURLService.jobseeker(profile.user, name, **kw)
        deadline = None
        if job.application_deadline:
            deadline = timezone.localtime(job.application_deadline).strftime(
                "%b %d, %Y"
            )

        return SavedJobCard(
            id=str(job.pk),
            saved_id=str(saved.pk),
            title=job.title,
            company_name=org_name,
            company_verified=True,
            logo_url=media_url(company.logo_file)
            if company and company.logo_file
            else None,
            logo_initial=(org_name[:1] or "E").upper(),
            location=location,
            salary_display=mapper._salary(
                job.salary_min, job.salary_max, job.salary_visibility
            ),
            experience_label=mapper._experience(job.experience_min),
            employment_type_label=job.get_employment_type_display(),
            work_mode_label=job.get_work_mode_display(),
            skills=skills,
            match_percent=match_percent,
            posted_display=mapper._posted(job.published_at or job.created_at),
            deadline_display=deadline,
            is_open=self._is_job_open(job),
            detail_url=detail_url,
            apply_url=apply_url,
            save_url=pu("jobseeker_save_job", job_id=job.pk),
            saved_at_display=timezone.localtime(saved.created_at).strftime("%b %d, %Y"),
        )

    @staticmethod
    def _is_job_open(job: JobPosting) -> bool:
        now = timezone.now()
        if job.is_deleted or job.status != JobStatus.PUBLISHED:
            return False
        if job.visibility != JobVisibility.PUBLIC:
            return False
        if job.expires_at and job.expires_at <= now:
            return False
        return True

    @staticmethod
    def login_url_with_save(next_path: str, job_id) -> str:
        detail = reverse("marketplace_job_detail", kwargs={"job_id": job_id})
        target = next_path or detail
        return f"{reverse('it_login_job_seeker')}?next={quote(target, safe='')}&save_job={job_id}"
