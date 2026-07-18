"""Recruiter posted jobs portal — enterprise job management dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.constants.enums import JobStatus, WorkMode
from apps.jobs.models import JobPosting, SavedJob
from apps.jobs.selectors.job_selector import JobPostingSelector


@dataclass
class RecruiterJobsPortalContext:
    jobs: list[dict]
    stats: dict
    has_company: bool
    can_publish: bool
    api_urls: dict
    companies: list[dict]
    pagination: dict
    filters: dict
    status_options: list[dict]
    application_status_options: list[dict]


class RecruiterJobsPortalService(BaseService):
    PER_PAGE = 15

    STATUS_FILTERS = [
        {"key": "", "label": "All"},
        {"key": JobStatus.PUBLISHED, "label": "Active"},
        {"key": JobStatus.DRAFT, "label": "Drafts"},
        {"key": JobStatus.PAUSED, "label": "Paused"},
        {"key": JobStatus.CLOSED, "label": "Closed"},
        {"key": JobStatus.ARCHIVED, "label": "Archived"},
    ]

    def build(
        self,
        profile: RecruiterProfile,
        *,
        status_filter: str = "",
        q: str = "",
        page: int = 1,
    ) -> RecruiterJobsPortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        memberships = (
            CompanyMemberSelector().for_recruiter(profile).select_related("company")
        )
        companies = [
            {
                "id": str(m.company_id),
                "name": m.company.name,
                "can_publish_jobs": m.company.can_publish_jobs,
            }
            for m in memberships
        ]
        has_company = bool(companies)
        can_publish = any(c["can_publish_jobs"] for c in companies)

        queryset = (
            JobPostingSelector()
            .for_recruiter(profile)
            .select_related("company")
            .order_by("-published_at", "-created_at")
        )
        if status_filter and status_filter in JobStatus.values:
            queryset = queryset.filter(status=status_filter)
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(department__icontains=q)
                | Q(location__icontains=q)
                | Q(city__icontains=q)
                | Q(company_name_snapshot__icontains=q)
            )

        paginator = Paginator(queryset, self.PER_PAGE)
        page_obj = paginator.get_page(page)
        job_ids = [job.pk for job in page_obj.object_list]
        metrics = self._bulk_job_metrics(job_ids)
        saved_counts = self._bulk_saved_counts(job_ids)

        jobs = [
            self._serialize_job(
                job,
                pu,
                metrics=metrics.get(str(job.pk), {}),
                saved_count=saved_counts.get(str(job.pk), 0),
            )
            for job in page_obj.object_list
        ]

        all_jobs = JobPostingSelector().for_recruiter(profile)
        stats = {
            "total": all_jobs.count(),
            "published": all_jobs.filter(status=JobStatus.PUBLISHED).count(),
            "draft": all_jobs.filter(status=JobStatus.DRAFT).count(),
            "paused": all_jobs.filter(status=JobStatus.PAUSED).count(),
            "closed": all_jobs.filter(status=JobStatus.CLOSED).count(),
            "archived": all_jobs.filter(status=JobStatus.ARCHIVED).count(),
        }

        return RecruiterJobsPortalContext(
            jobs=jobs,
            stats=stats,
            has_company=has_company,
            can_publish=can_publish,
            companies=companies,
            pagination={
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "start_index": page_obj.start_index() if paginator.count else 0,
                "end_index": page_obj.end_index() if paginator.count else 0,
            },
            filters={"q": q, "status": status_filter},
            status_options=self.STATUS_FILTERS,
            application_status_options=[
                {"value": choice.value, "label": choice.label}
                for choice in JobApplicationStatus
            ],
            api_urls=self._api_urls(pu),
        )

    @staticmethod
    def _api_urls(pu) -> dict:
        placeholder_job = "00000000-0000-0000-0000-000000000000"
        placeholder_app = "00000000-0000-0000-0000-000000000000"
        return {
            "list": pu("recruiter_jobs_list_api"),
            "create_job": pu("recruiter_job_create_api"),
            "skill_suggest": pu("recruiter_skill_suggest_api"),
            "job_detail_template": pu(
                "recruiter_job_detail_api", job_id=placeholder_job
            ),
            "publish_template": pu("recruiter_job_publish_api", job_id=placeholder_job),
            "close_template": pu("recruiter_job_close_api", job_id=placeholder_job),
            "pause_template": pu("recruiter_job_pause_api", job_id=placeholder_job),
            "reopen_template": pu("recruiter_job_reopen_api", job_id=placeholder_job),
            "duplicate_template": pu(
                "recruiter_job_duplicate_api", job_id=placeholder_job
            ),
            "archive_template": pu("recruiter_job_archive_api", job_id=placeholder_job),
            "delete_template": pu("recruiter_job_delete_api", job_id=placeholder_job),
            "applicants_template": pu(
                "recruiter_job_applicants_api", job_id=placeholder_job
            ),
            "status_template": pu(
                "recruiter_application_status_api", application_id=placeholder_app
            ),
            "notes_template": pu(
                "recruiter_application_notes_api", application_id=placeholder_app
            ),
            "resume_template": pu(
                "recruiter_application_resume_api", application_id=placeholder_app
            ),
            "detail_template": pu(
                "recruiter_application_detail_api", application_id=placeholder_app
            ),
            "interview_schedule_template": pu(
                "recruiter_interview_schedule_api", application_id=placeholder_app
            ),
        }

    @staticmethod
    def _bulk_job_metrics(job_ids: list) -> dict[str, dict[str, int]]:
        if not job_ids:
            return {}
        rows = (
            JobApplication.objects.filter(job_posting_id__in=job_ids, is_deleted=False)
            .values("job_posting_id", "status")
            .annotate(c=Count("id"))
        )
        metrics: dict[str, dict[str, int]] = {}
        for row in rows:
            jid = str(row["job_posting_id"])
            metrics.setdefault(jid, {})
            metrics[jid][row["status"]] = row["c"]
        return metrics

    @staticmethod
    def _bulk_saved_counts(job_ids: list) -> dict[str, int]:
        if not job_ids:
            return {}
        rows = (
            SavedJob.objects.filter(job_posting_id__in=job_ids, is_deleted=False)
            .values("job_posting_id")
            .annotate(c=Count("id"))
        )
        return {str(row["job_posting_id"]): row["c"] for row in rows}

    @classmethod
    def _serialize_job(
        cls,
        job: JobPosting,
        pu,
        *,
        metrics: dict[str, int] | None = None,
        saved_count: int = 0,
    ) -> dict:
        metrics = metrics or {}
        total_apps = sum(metrics.values()) or job.application_count
        shortlisted = metrics.get(JobApplicationStatus.SHORTLISTED, 0)
        interviews = metrics.get(
            JobApplicationStatus.INTERVIEW_SCHEDULED, 0
        ) + metrics.get(JobApplicationStatus.INTERVIEW_COMPLETED, 0)
        offers = metrics.get(JobApplicationStatus.OFFER_RELEASED, 0) + metrics.get(
            JobApplicationStatus.OFFER_ACCEPTED, 0
        )
        hired = metrics.get(JobApplicationStatus.HIRED, 0)
        rejected = metrics.get(JobApplicationStatus.REJECTED, 0)
        conversion = round((hired / total_apps) * 100, 1) if total_apps else 0

        status_label = job.get_status_display()
        published_label = (
            timezone.localtime(job.published_at).strftime("%b %d, %Y")
            if job.published_at
            else "—"
        )
        expiry_label = "—"
        if job.application_deadline:
            expiry_label = timezone.localtime(job.application_deadline).strftime(
                "%b %d, %Y"
            )
        elif job.expires_at:
            expiry_label = timezone.localtime(job.expires_at).strftime("%b %d, %Y")

        req_skills = []
        pref_skills = []
        if hasattr(job, "required_skills"):
            for jps in job.required_skills.select_related("skill").all():
                if jps.is_preferred:
                    pref_skills.append(jps.skill.name)
                else:
                    req_skills.append(jps.skill.name)

        raw_data = {
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements or "",
            "location": job.location or "",
            "is_remote": job.is_remote,
            "employment_type": job.employment_type,
            "work_mode": job.work_mode or "onsite",
            "experience_min": job.experience_min,
            "experience_max": job.experience_max,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency or "INR",
            "salary_visibility": job.salary_visibility or "visible",
            "vacancies": job.vacancies,
            "job_code": job.job_code or "",
            "category": job.category or "",
            "department": job.department or "",
            "roles_responsibilities": job.roles_responsibilities or "",
            "benefits": job.benefits or "",
            "education_requirement": job.education_requirement or "",
            "joining_timeline": job.joining_timeline or "",
            "application_deadline": job.application_deadline.isoformat()
            if job.application_deadline
            else "",
            "country": job.country or "",
            "state": job.state or "",
            "city": job.city or "",
            "office_address": job.office_address or "",
            "required_skills": req_skills,
            "preferred_skills": pref_skills,
        }

        return {
            "id": str(job.pk),
            "title": job.title,
            "company_name": job.company_name_snapshot or job.company.name,
            "department": job.department or job.category or "General",
            "employment_type": job.get_employment_type_display(),
            "work_mode": cls._work_mode_label(job),
            "location": job.location
            or job.city
            or ("Remote" if job.is_remote else "—"),
            "salary_range": cls._salary_range(job),
            "experience_label": cls._experience_label(job),
            "status": job.status,
            "status_label": status_label,
            "status_tone": cls._status_tone(job.status),
            "application_count": total_apps,
            "shortlisted_count": shortlisted,
            "interview_count": interviews,
            "offer_count": offers,
            "hired_count": hired,
            "rejected_count": rejected,
            "view_count": job.view_count,
            "saved_count": saved_count,
            "conversion_rate": conversion,
            "published_label": published_label,
            "expiry_label": expiry_label,
            "created_label": timezone.localtime(job.created_at).strftime("%b %d, %Y"),
            "badges": cls._job_badges(job),
            "applicants_url": pu("recruiter_candidates") + f"?job_id={job.pk}",
            "edit_url": pu("recruiter_job_edit", job_id=job.pk),
            "detail_api_url": pu("recruiter_job_detail_api", job_id=job.pk),
            "publish_url": pu("recruiter_job_publish_api", job_id=job.pk),
            "close_url": pu("recruiter_job_close_api", job_id=job.pk),
            "pause_url": pu("recruiter_job_pause_api", job_id=job.pk),
            "reopen_url": pu("recruiter_job_reopen_api", job_id=job.pk),
            "duplicate_url": pu("recruiter_job_duplicate_api", job_id=job.pk),
            "archive_url": pu("recruiter_job_archive_api", job_id=job.pk),
            "delete_url": pu("recruiter_job_delete_api", job_id=job.pk),
            "applicants_api_url": pu("recruiter_job_applicants_api", job_id=job.pk),
            "can_publish": job.status == JobStatus.DRAFT
            and job.company.can_publish_jobs,
            "can_close": job.status
            in (JobStatus.DRAFT, JobStatus.PUBLISHED, JobStatus.PAUSED),
            "can_pause": job.status == JobStatus.PUBLISHED,
            "can_reopen": job.status in (JobStatus.PAUSED, JobStatus.CLOSED)
            and job.company.can_publish_jobs,
            "can_duplicate": True,
            "can_archive": job.status
            in (JobStatus.CLOSED, JobStatus.EXPIRED, JobStatus.PAUSED),
            "can_delete": job.status
            in (
                JobStatus.DRAFT,
                JobStatus.CLOSED,
                JobStatus.PAUSED,
                JobStatus.ARCHIVED,
            ),
            "raw": raw_data,
            "analytics": {
                "applications": total_apps,
                "views": job.view_count,
                "saves": saved_count,
                "shortlisted": shortlisted,
                "interviews": interviews,
                "offers": offers,
                "hired": hired,
                "rejected": rejected,
                "conversion_rate": conversion,
            },
        }

    @staticmethod
    def _work_mode_label(job: JobPosting) -> str:
        if job.is_remote or job.work_mode == WorkMode.REMOTE:
            return "Remote"
        if job.work_mode == WorkMode.HYBRID:
            return "Hybrid"
        return job.get_work_mode_display() if job.work_mode else "On-site"

    @staticmethod
    def _experience_label(job: JobPosting) -> str:
        if job.experience_min is not None and job.experience_max is not None:
            return f"{job.experience_min}–{job.experience_max} yrs"
        if job.experience_min is not None:
            return f"{job.experience_min}+ yrs"
        if job.experience_max is not None:
            return f"Up to {job.experience_max} yrs"
        return "—"

    @staticmethod
    def _salary_range(job: JobPosting) -> str:
        if job.salary_min and job.salary_max:
            return f"₹{int(job.salary_min):,} – ₹{int(job.salary_max):,}"
        if job.salary_min:
            return f"From ₹{int(job.salary_min):,}"
        if job.salary_max:
            return f"Up to ₹{int(job.salary_max):,}"
        return "—"

    @staticmethod
    def _status_tone(status: str) -> str:
        tones = {
            JobStatus.PUBLISHED: "success",
            JobStatus.DRAFT: "muted",
            JobStatus.PAUSED: "warning",
            JobStatus.CLOSED: "danger",
            JobStatus.ARCHIVED: "muted",
            JobStatus.EXPIRED: "warning",
        }
        return tones.get(status, "primary")

    @staticmethod
    def _job_badges(job: JobPosting) -> list[str]:
        badges = []
        if job.is_urgent:
            badges.append("urgent")
        if job.is_featured:
            badges.append("featured")
        if job.published_at and (timezone.now() - job.published_at).days <= 7:
            badges.append("new")
        return badges
