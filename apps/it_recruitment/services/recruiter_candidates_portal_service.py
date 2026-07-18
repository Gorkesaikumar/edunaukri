"""Recruiter candidates portal — application pipeline for company jobs."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.applications.selectors.application_selector import ApplicationSearchSelector
from apps.applications.services.application_statistics_service import (
    ApplicationStatisticsService,
)
from apps.applications.workflow.engine import ApplicationWorkflowEngine
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import (
    JobSeekerEducation,
    JobSeekerExperience,
    RecruiterProfile,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_expected_salary_lpa,
    initials_from_name,
    media_url,
)
from apps.jobs.models import JobSeekerSkill
from apps.jobs.selectors.job_selector import JobPostingSelector


@dataclass
class RecruiterCandidatesPortalContext:
    applications: list[dict]
    stats: dict
    analytics: list[dict]
    status_options: list[dict]
    job_filters: list[dict]
    filters: dict
    api_urls: dict
    pagination: dict
    sort_options: list[dict]


class RecruiterCandidatesPortalService(BaseService):
    STATUS_LABELS = dict(JobApplicationStatus.choices)
    PER_PAGE = 20

    SORT_OPTIONS = [
        {"key": "recent", "label": "Most Recent"},
        {"key": "oldest", "label": "Oldest First"},
        {"key": "name", "label": "Name A–Z"},
        {"key": "status", "label": "Status"},
    ]

    def build(
        self,
        profile: RecruiterProfile,
        *,
        q: str = "",
        status: str = "",
        job_id: str = "",
        location: str = "",
        experience_min: str = "",
        skills: str = "",
        education: str = "",
        date_from: str = "",
        date_to: str = "",
        sort: str = "recent",
        page: int = 1,
    ) -> RecruiterCandidatesPortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        stats = ApplicationStatisticsService().recruiter_dashboard(profile)

        qs = self._build_queryset(
            profile,
            q=q,
            status=status,
            job_id=job_id,
            location=location,
            experience_min=experience_min,
            skills=skills,
            education=education,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )
        paginator = Paginator(qs, self.PER_PAGE)
        page_obj = paginator.get_page(page)

        job_filters = [
            {"id": str(job.pk), "title": job.title}
            for job in JobPostingSelector()
            .for_recruiter(profile)
            .only("pk", "title")[:50]
        ]

        return RecruiterCandidatesPortalContext(
            applications=[self._serialize_app(app, pu) for app in page_obj.object_list],
            stats=stats,
            analytics=self._analytics_cards(
                stats.get("applications_by_status", {}),
                stats.get("active_applications", 0),
            ),
            status_options=[
                {"value": choice.value, "label": choice.label}
                for choice in JobApplicationStatus
            ],
            job_filters=job_filters,
            filters={
                "q": q,
                "status": status,
                "job_id": job_id,
                "location": location,
                "experience_min": experience_min,
                "skills": skills,
                "education": education,
                "date_from": date_from,
                "date_to": date_to,
                "sort": sort,
            },
            pagination={
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "start_index": page_obj.start_index() if paginator.count else 0,
                "end_index": page_obj.end_index() if paginator.count else 0,
            },
            sort_options=self.SORT_OPTIONS,
            api_urls={
                "list": pu("recruiter_applicants_list_api"),
                "status_template": pu(
                    "recruiter_application_status_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "notes_template": pu(
                    "recruiter_application_notes_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "resume_template": pu(
                    "recruiter_application_resume_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "detail_template": pu(
                    "recruiter_application_detail_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "interview_schedule_template": pu(
                    "recruiter_interview_schedule_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "messages_url": pu("recruiter_messages"),
            },
        )

    def build_list_payload(
        self,
        profile: RecruiterProfile,
        *,
        q: str = "",
        status: str = "",
        job_id: str = "",
        location: str = "",
        experience_min: str = "",
        skills: str = "",
        education: str = "",
        date_from: str = "",
        date_to: str = "",
        sort: str = "recent",
        page: int = 1,
    ) -> dict:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        stats = ApplicationStatisticsService().recruiter_dashboard(profile)
        qs = self._build_queryset(
            profile,
            q=q,
            status=status,
            job_id=job_id,
            location=location,
            experience_min=experience_min,
            skills=skills,
            education=education,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )
        paginator = Paginator(qs, self.PER_PAGE)
        page_obj = paginator.get_page(page)
        return {
            "success": True,
            "applications": [
                self._serialize_app(app, pu) for app in page_obj.object_list
            ],
            "analytics": self._analytics_cards(
                stats.get("applications_by_status", {}),
                stats.get("active_applications", 0),
            ),
            "pagination": {
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "start_index": page_obj.start_index() if paginator.count else 0,
                "end_index": page_obj.end_index() if paginator.count else 0,
            },
        }

    def _build_queryset(
        self,
        profile: RecruiterProfile,
        *,
        q: str = "",
        status: str = "",
        job_id: str = "",
        location: str = "",
        experience_min: str = "",
        skills: str = "",
        education: str = "",
        date_from: str = "",
        date_to: str = "",
        sort: str = "recent",
    ):
        qs = ApplicationSearchSelector().search(
            query="",
            status=status,
            job_posting_id=job_id or None,
            recruiter=profile,
            sort="recent",
        )
        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(job_title_snapshot__icontains=q)
                | Q(current_location__icontains=q)
                | Q(job_seeker__user__email__icontains=q)
                | Q(job_seeker__phone__icontains=q)
                | Q(job_seeker__skills__skill__name__icontains=q)
            ).distinct()
        if location:
            qs = qs.filter(
                Q(current_location__icontains=location)
                | Q(job_seeker__current_location__icontains=location)
                | Q(job_seeker__city__icontains=location)
            )
        if experience_min:
            try:
                qs = qs.filter(job_seeker__experience_years__gte=int(experience_min))
            except ValueError:
                pass
        if skills:
            skill_list = [s.strip() for s in skills.split(",") if s.strip()]
            for sk in skill_list:
                qs = qs.filter(job_seeker__skills__skill__name__icontains=sk)
            qs = qs.distinct()
        if education:
            qs = qs.filter(
                Q(job_seeker__education__degree__icontains=education)
                | Q(job_seeker__education__institution__icontains=education)
                | Q(job_seeker__education__field_of_study__icontains=education)
            ).distinct()
        if date_from:
            qs = qs.filter(applied_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(applied_at__date__lte=date_to)

        order_map = {
            "recent": "-applied_at",
            "oldest": "applied_at",
            "name": "applicant_name_snapshot",
            "status": "status",
        }
        qs = qs.select_related(
            "job_seeker",
            "job_seeker__profile_photo",
            "job_seeker__resume_file",
            "job_seeker__user",
            "job_posting",
        ).prefetch_related(
            Prefetch(
                "job_seeker__skills",
                queryset=JobSeekerSkill.objects.select_related("skill").filter(
                    is_deleted=False
                ),
            ),
        )
        return qs.order_by(order_map.get(sort, "-applied_at"))

    def list_for_job(
        self,
        profile: RecruiterProfile,
        job_id,
        *,
        q: str = "",
        status: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        job = JobPostingSelector().for_recruiter(profile).filter(pk=job_id).first()
        if not job:
            return {"success": False, "error": "Job not found."}

        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        qs = ApplicationSearchSelector().search(
            query="",
            status=status,
            job_posting_id=job_id,
            recruiter=profile,
            sort="recent",
        )
        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(job_title_snapshot__icontains=q)
                | Q(current_location__icontains=q)
                | Q(job_seeker__user__email__icontains=q)
                | Q(job_seeker__phone__icontains=q)
                | Q(job_seeker__skills__skill__name__icontains=q)
            ).distinct()
        qs = qs.select_related(
            "job_seeker",
            "job_seeker__profile_photo",
            "job_seeker__resume_file",
            "job_seeker__user",
            "job_posting",
        ).prefetch_related(
            Prefetch(
                "job_seeker__skills",
                queryset=JobSeekerSkill.objects.select_related("skill").filter(
                    is_deleted=False
                ),
            ),
            Prefetch(
                "job_seeker__experiences",
                queryset=JobSeekerExperience.objects.filter(is_deleted=False).order_by(
                    "-start_date"
                ),
            ),
            Prefetch(
                "job_seeker__education",
                queryset=JobSeekerEducation.objects.filter(is_deleted=False).order_by(
                    "-end_year"
                ),
            ),
        )

        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)
        return {
            "success": True,
            "job": {"id": str(job.pk), "title": job.title},
            "applications": [
                self._serialize_app(app, pu, extended=True)
                for app in page_obj.object_list
            ],
            "pagination": {
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            "filters": {"q": q, "status": status},
        }

    def get_detail(self, profile: RecruiterProfile, application_id) -> dict | None:
        from django.db.models import Prefetch

        from apps.it_recruitment.models import (
            JobSeekerCertification,
            JobSeekerEducation,
            JobSeekerExperience,
        )

        application = (
            JobApplication.objects.filter(pk=application_id, is_deleted=False)
            .select_related(
                "job_seeker",
                "job_seeker__user",
                "job_seeker__profile_photo",
                "job_seeker__resume_file",
                "job_posting",
            )
            .prefetch_related(
                Prefetch(
                    "job_seeker__skills",
                    queryset=JobSeekerSkill.objects.select_related("skill").filter(
                        is_deleted=False
                    ),
                ),
                Prefetch(
                    "job_seeker__experiences",
                    queryset=JobSeekerExperience.objects.filter(
                        is_deleted=False
                    ).order_by("-start_date"),
                ),
                Prefetch(
                    "job_seeker__education",
                    queryset=JobSeekerEducation.objects.filter(
                        is_deleted=False
                    ).order_by("-end_year"),
                ),
                Prefetch(
                    "job_seeker__certifications",
                    queryset=JobSeekerCertification.objects.filter(is_deleted=False),
                ),
            )
            .first()
        )
        if not application:
            return None
        from apps.applications.services.application_authorization_service import (
            ApplicationAuthorizationService,
        )
        from apps.core.exceptions.domain_exceptions import PermissionDeniedException

        try:
            ApplicationAuthorizationService().ensure_can_view_it_application(
                application, profile.user
            )
        except PermissionDeniedException:
            return None
        pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
        return self._serialize_app(application, pu, extended=True)

    def _serialize_app(
        self, app: JobApplication, pu, *, extended: bool = False
    ) -> dict:
        next_statuses = sorted(
            ApplicationWorkflowEngine.transitions.get(app.status, set()),
            key=lambda s: self.STATUS_LABELS.get(s, s),
        )
        seeker = app.job_seeker
        skills = []
        if hasattr(seeker, "skills"):
            skills = [
                link.skill.name
                for link in seeker.skills.all()
                if getattr(link, "skill", None)
            ][:12]

        data = {
            "id": str(app.pk),
            "applicant_name": app.applicant_name_snapshot,
            "initials": initials_from_name(app.applicant_name_snapshot, "JS"),
            "email": getattr(seeker.user, "email", "") if seeker else "",
            "phone": seeker.phone if seeker else "",
            "job_title": app.job_title_snapshot,
            "company_name": app.company_name_snapshot,
            "status": app.status,
            "status_label": self.STATUS_LABELS.get(
                app.status, app.status.replace("_", " ").title()
            ),
            "applied_label": timezone.localtime(app.applied_at).strftime("%b %d, %Y"),
            "location": app.current_location
            or (seeker.current_location if seeker else "")
            or "—",
            "current_company": seeker.current_company if seeker else "—",
            "experience_years": seeker.experience_years
            if seeker and seeker.experience_years is not None
            else "—",
            "education": self._education_summary(seeker) if seeker else "—",
            "skills": skills,
            "skills_label": ", ".join(skills[:6]) if skills else "—",
            "notice_period": app.notice_period or "—",
            "expected_salary": format_expected_salary_lpa(app.expected_salary)
            if app.expected_salary
            else "—",
            "recruiter_notes": app.recruiter_notes,
            "is_terminal": ApplicationWorkflowEngine.is_terminal(app.status),
            "next_statuses": [
                {
                    "value": s,
                    "label": self.STATUS_LABELS.get(s, s.replace("_", " ").title()),
                }
                for s in next_statuses
            ],
            "status_url": pu("recruiter_application_status_api", application_id=app.pk),
            "notes_url": pu("recruiter_application_notes_api", application_id=app.pk),
            "resume_url": pu("recruiter_application_resume_api", application_id=app.pk),
            "resume_preview_url": pu(
                "recruiter_application_resume_api", application_id=app.pk
            )
            + "?preview=1",
            "detail_url": pu("recruiter_application_detail_api", application_id=app.pk),
            "interview_schedule_url": pu(
                "recruiter_interview_schedule_api", application_id=app.pk
            ),
            "has_resume": bool(
                app.resume_file_id or getattr(seeker, "resume_file_id", None)
            ),
            "photo_url": self._photo_url(seeker),
            "stage_label": self.STATUS_LABELS.get(
                app.status, app.status.replace("_", " ").title()
            ),
            "status_tone": self._status_tone(app.status),
            "messages_url": pu("recruiter_messages"),
            "email_url": f"mailto:{getattr(seeker.user, 'email', '')}"
            if seeker and getattr(seeker.user, "email", None)
            else "",
        }
        if extended:
            data.update(self._extended_profile(app, seeker))
        return data

    @staticmethod
    def _status_tone(status: str) -> str:
        tones = {
            JobApplicationStatus.APPLIED: "muted",
            JobApplicationStatus.UNDER_REVIEW: "primary",
            JobApplicationStatus.SHORTLISTED: "success",
            JobApplicationStatus.INTERVIEW_SCHEDULED: "primary",
            JobApplicationStatus.INTERVIEW_COMPLETED: "primary",
            JobApplicationStatus.OFFER_RELEASED: "warning",
            JobApplicationStatus.OFFER_ACCEPTED: "success",
            JobApplicationStatus.HIRED: "success",
            JobApplicationStatus.REJECTED: "danger",
            JobApplicationStatus.WITHDRAWN: "muted",
        }
        return tones.get(status, "primary")

    @staticmethod
    def _photo_url(seeker) -> str:
        if not seeker or not seeker.profile_photo_id:
            return ""
        return media_url(seeker.profile_photo) or ""

    @staticmethod
    def _education_summary(seeker) -> str:
        if not seeker:
            return "—"
        edu = seeker.education.all()[:1]
        if not edu:
            return "—"
        row = edu[0]
        parts = [row.degree or row.institution or ""]
        if row.end_year:
            parts.append(str(row.end_year))
        return " · ".join(p for p in parts if p) or "—"

    @staticmethod
    def _extended_profile(app: JobApplication, seeker) -> dict:
        experiences = []
        certifications = []
        education_rows = []
        if seeker:
            experiences = [
                {
                    "title": exp.title or "Role",
                    "company": exp.company_name or "—",
                    "duration": "",
                }
                for exp in seeker.experiences.all()[:5]
            ]
            education_rows = [
                {
                    "degree": edu.degree or edu.get_education_level_display(),
                    "institution": edu.institution or "—",
                    "year": edu.end_year or "",
                }
                for edu in seeker.education.all()[:3]
            ]
            certifications = [
                {"name": cert.name, "issuer": cert.issuing_organization or ""}
                for cert in seeker.certifications.all()[:5]
            ]
        address_parts = []
        if seeker:
            for part in (seeker.city, seeker.state, seeker.country):
                if part:
                    address_parts.append(part)
        return {
            "headline": seeker.headline if seeker else "",
            "summary": seeker.summary if seeker else "",
            "address": ", ".join(address_parts) or "—",
            "linkedin_url": seeker.linkedin_url if seeker else "",
            "github_url": seeker.github_url if seeker else "",
            "portfolio_url": seeker.portfolio_url
            or (seeker.personal_website if seeker else "")
            or "",
            "languages": seeker.languages if seeker else [],
            "experiences": experiences,
            "education_rows": education_rows,
            "certifications": certifications,
            "applied_job": app.job_title_snapshot,
            "current_stage": app.get_status_display()
            if hasattr(app, "get_status_display")
            else app.status,
        }

    @staticmethod
    def _analytics_cards(by_status: dict, active: int) -> list[dict]:
        return [
            {
                "key": "total",
                "label": "Total",
                "value": sum(by_status.values()),
                "icon": "group",
                "tone": "primary",
            },
            {
                "key": "active",
                "label": "Active",
                "value": active,
                "icon": "bolt",
                "tone": "secondary",
            },
            {
                "key": "applied",
                "label": "New (Applied)",
                "value": by_status.get(JobApplicationStatus.APPLIED, 0),
                "icon": "person_add",
                "tone": "primary",
            },
            {
                "key": "review",
                "label": "Reviewed",
                "value": by_status.get(JobApplicationStatus.UNDER_REVIEW, 0),
                "icon": "visibility",
                "tone": "primary",
            },
            {
                "key": "shortlisted",
                "label": "Shortlisted",
                "value": by_status.get(JobApplicationStatus.SHORTLISTED, 0),
                "icon": "star",
                "tone": "tertiary",
            },
            {
                "key": "interview",
                "label": "Interview Scheduled",
                "value": by_status.get(JobApplicationStatus.INTERVIEW_SCHEDULED, 0),
                "icon": "calendar_today",
                "tone": "primary",
            },
            {
                "key": "interview_completed",
                "label": "Interview Completed",
                "value": by_status.get(JobApplicationStatus.INTERVIEW_COMPLETED, 0),
                "icon": "fact_check",
                "tone": "secondary",
            },
            {
                "key": "offered",
                "label": "Offered",
                "value": by_status.get(JobApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(JobApplicationStatus.OFFER_ACCEPTED, 0),
                "icon": "description",
                "tone": "success",
            },
            {
                "key": "hired",
                "label": "Hired",
                "value": by_status.get(JobApplicationStatus.HIRED, 0),
                "icon": "emoji_events",
                "tone": "success",
            },
            {
                "key": "rejected",
                "label": "Rejected",
                "value": by_status.get(JobApplicationStatus.REJECTED, 0),
                "icon": "cancel",
                "tone": "danger",
            },
        ]
