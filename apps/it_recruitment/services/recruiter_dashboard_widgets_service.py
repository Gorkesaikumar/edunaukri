"""Enhanced dashboard widgets — pipeline, jobs, interviews, analytics, activity."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from django.utils.timesince import timesince

from apps.applications.constants.enums import (
    ApplicationSource,
    JobApplicationStatus,
    TimelineEventType,
)
from apps.applications.constants.interview_enums import InterviewMode, InterviewStatus
from apps.applications.models import JobApplication, JobApplicationTimelineEvent
from apps.applications.models.interview import JobApplicationInterview
from apps.applications.workflow.engine import ApplicationWorkflowEngine
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_expected_salary_lpa,
    media_url,
)
from apps.it_recruitment.services.recruiter_dashboard_kpi_service import (
    RecruiterDashboardKPIService,
)
from apps.jobs.constants.enums import EmploymentType, JobStatus, WorkMode
from apps.jobs.models import JobPosting
from apps.jobs.selectors.job_selector import JobPostingSelector
from apps.notifications.models import Notification

from apps.it_recruitment.services.jobseeker_portal_helpers import initials_from_name

PIPELINE_STAGES = (
    {
        "key": "screening",
        "label": "Screening",
        "statuses": (JobApplicationStatus.APPLIED, JobApplicationStatus.UNDER_REVIEW),
        "target_status": JobApplicationStatus.UNDER_REVIEW,
        "accent": "secondary",
    },
    {
        "key": "shortlisted",
        "label": "Shortlisted",
        "statuses": (JobApplicationStatus.SHORTLISTED,),
        "target_status": JobApplicationStatus.SHORTLISTED,
        "accent": "tertiary",
    },
    {
        "key": "interview_scheduled",
        "label": "Interview Scheduled",
        "statuses": (JobApplicationStatus.INTERVIEW_SCHEDULED,),
        "target_status": JobApplicationStatus.INTERVIEW_SCHEDULED,
        "accent": "primary",
    },
    {
        "key": "interview_completed",
        "label": "Interview Completed",
        "statuses": (JobApplicationStatus.INTERVIEW_COMPLETED,),
        "target_status": JobApplicationStatus.INTERVIEW_COMPLETED,
        "accent": "primary",
    },
    {
        "key": "selected",
        "label": "Selected",
        "statuses": (JobApplicationStatus.OFFER_ACCEPTED,),
        "target_status": JobApplicationStatus.OFFER_ACCEPTED,
        "accent": "tertiary",
    },
    {
        "key": "offered",
        "label": "Offered",
        "statuses": (JobApplicationStatus.OFFER_RELEASED,),
        "target_status": JobApplicationStatus.OFFER_RELEASED,
        "accent": "secondary",
    },
    {
        "key": "hired",
        "label": "Hired",
        "statuses": (JobApplicationStatus.HIRED,),
        "target_status": JobApplicationStatus.HIRED,
        "accent": "success",
    },
    {
        "key": "rejected",
        "label": "Rejected",
        "statuses": (JobApplicationStatus.REJECTED,),
        "target_status": JobApplicationStatus.REJECTED,
        "accent": "danger",
    },
)

SOURCE_LABELS = {
    ApplicationSource.DIRECT: "Direct Applications",
    ApplicationSource.REFERRAL: "Referrals",
    ApplicationSource.JOB_BOARD: "Job Boards",
    ApplicationSource.AGENCY: "Agency",
    ApplicationSource.CAREER_FAIR: "Career Fair",
    ApplicationSource.INTERNAL: "EduNaukri Portal",
    ApplicationSource.OTHER: "Other Sources",
    "": "EduNaukri Portal",
    "direct": "Direct Applications",
    "referral": "Referrals",
    "job_board": "Job Boards",
    "linkedin": "LinkedIn",
    "company_website": "Company Website",
    "google_jobs": "Google Jobs",
    "indeed": "Indeed",
    "naukri": "Naukri",
    "employee_referral": "Employee Referral",
}


@dataclass
class DashboardFilters:
    job_id: str = ""
    department: str = ""
    status: str = ""
    location: str = ""
    date_from: str = ""
    date_to: str = ""
    source: str = ""
    analytics_period: str = "7d"

    @classmethod
    def from_request(cls, request) -> DashboardFilters:
        return cls(
            job_id=(request.GET.get("job_id") or "").strip(),
            department=(request.GET.get("department") or "").strip(),
            status=(request.GET.get("status") or "").strip(),
            location=(request.GET.get("location") or "").strip(),
            date_from=(request.GET.get("date_from") or "").strip(),
            date_to=(request.GET.get("date_to") or "").strip(),
            source=(request.GET.get("source") or "").strip(),
            analytics_period=(
                request.GET.get("analytics_period") or request.GET.get("period") or "7d"
            ).strip(),
        )


class RecruiterDashboardWidgetsService(BaseService):
    def __init__(self):
        self.kpi = RecruiterDashboardKPIService()

    def build_all(
        self,
        profile: RecruiterProfile,
        *,
        filters: DashboardFilters | None = None,
    ) -> dict:
        filters = filters or DashboardFilters()
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        apps_qs = self._filtered_apps(profile, filters)
        jobs_qs = JobPostingSelector().for_recruiter(profile).select_related("company")

        return {
            "pipeline": self.build_pipeline(apps_qs, pu, filters),
            "active_jobs": self.build_active_jobs(profile, apps_qs, pu, filters),
            "upcoming_interviews": self.build_interviews(profile, pu, filters),
            "candidate_sources": self.build_candidate_sources(apps_qs, filters),
            "recent_activity": self.build_activity(apps_qs, pu),
            "notifications": self.build_notifications(profile, pu),
            "analytics": self.build_analytics(
                apps_qs, jobs_qs, profile=profile, period=filters.analytics_period
            ),
            "filter_options": self.build_filter_options(profile, apps_qs),
            "filters": {
                "job_id": filters.job_id,
                "department": filters.department,
                "status": filters.status,
                "location": filters.location,
                "date_from": filters.date_from,
                "date_to": filters.date_to,
                "source": filters.source,
                "analytics_period": filters.analytics_period,
            },
            "api_urls": {
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
                "publish_template": pu(
                    "recruiter_job_publish_api",
                    job_id="00000000-0000-0000-0000-000000000000",
                ),
                "close_template": pu(
                    "recruiter_job_close_api",
                    job_id="00000000-0000-0000-0000-000000000000",
                ),
                "pause_template": pu(
                    "recruiter_job_pause_api",
                    job_id="00000000-0000-0000-0000-000000000000",
                ),
                "duplicate_template": pu(
                    "recruiter_job_duplicate_api",
                    job_id="00000000-0000-0000-0000-000000000000",
                ),
                "delete_template": pu(
                    "recruiter_job_delete_api",
                    job_id="00000000-0000-0000-0000-000000000000",
                ),
                "interview_cancel_template": pu(
                    "recruiter_interview_cancel_api",
                    interview_id="00000000-0000-0000-0000-000000000000",
                ),
                "interview_reschedule_template": pu(
                    "recruiter_interview_reschedule_api",
                    interview_id="00000000-0000-0000-0000-000000000000",
                ),
                "analytics_export": pu("recruiter_analytics_export_api"),
            },
        }

    def _filtered_apps(
        self, profile: RecruiterProfile, filters: DashboardFilters
    ) -> QuerySet:
        qs = self.kpi.applications_qs(profile).select_related(
            "job_posting", "job_seeker", "job_seeker__profile_photo"
        )
        if filters.job_id:
            qs = qs.filter(job_posting_id=filters.job_id)
        if filters.department:
            qs = qs.filter(job_posting__department__icontains=filters.department)
        if filters.status:
            qs = qs.filter(status=filters.status)
        if filters.location:
            qs = qs.filter(
                Q(current_location__icontains=filters.location)
                | Q(job_posting__location__icontains=filters.location)
                | Q(job_posting__city__icontains=filters.location)
            )
        if filters.source:
            qs = qs.filter(source=filters.source)
        if filters.date_from:
            qs = qs.filter(applied_at__date__gte=filters.date_from)
        if filters.date_to:
            qs = qs.filter(applied_at__date__lte=filters.date_to)
        return qs

    def build_pipeline(
        self, apps_qs: QuerySet, pu, filters: DashboardFilters
    ) -> list[dict]:
        columns = []
        for stage in PIPELINE_STAGES:
            col_qs = apps_qs.filter(status__in=stage["statuses"]).order_by(
                "-applied_at"
            )
            count = col_qs.count()
            cards = []
            for app in col_qs[:5]:
                cards.append(self._pipeline_card(app, stage, pu))
            columns.append(
                {
                    "key": stage["key"],
                    "label": stage["label"],
                    "count": count,
                    "accent": stage["accent"],
                    "target_status": stage["target_status"],
                    "cards": cards,
                }
            )
        return columns

    def _pipeline_card(self, app: JobApplication, stage: dict, pu) -> dict:
        seeker = app.job_seeker
        skills = (
            list(
                seeker.skills.select_related("skill").values_list(
                    "skill__name", flat=True
                )[:4]
            )
            if seeker
            else []
        )
        if not skills and app.resume_snapshot:
            skills = (app.resume_snapshot.get("skills") or [])[:4]
        exp = (
            seeker.experience_years
            if seeker and seeker.experience_years is not None
            else None
        )
        if exp is None and app.resume_snapshot:
            exp = app.resume_snapshot.get("experience_years")
        exp_label = f"{exp} yr{'s' if exp != 1 else ''}" if exp is not None else "—"
        photo_url = None
        if seeker and seeker.profile_photo:
            photo_url = media_url(seeker.profile_photo)
        transitions = ApplicationWorkflowEngine.transitions.get(app.status, set())
        can_drag = stage["target_status"] in transitions
        status_labels = dict(JobApplicationStatus.choices)
        next_statuses = sorted(transitions, key=lambda s: status_labels.get(s, s))
        detail = {
            "location": app.current_location
            or (seeker.current_location if seeker else "")
            or "—",
            "expected_salary": format_expected_salary_lpa(app.expected_salary)
            if app.expected_salary
            else "—",
            "notice_period": app.notice_period or "—",
            "company": app.company_name_snapshot,
            "status_label": status_labels.get(app.status, app.status),
        }
        return {
            "id": str(app.pk),
            "name": app.applicant_name_snapshot,
            "job_title": app.job_title_snapshot,
            "experience": exp_label,
            "skills": skills,
            "applied_label": timezone.localtime(app.applied_at).strftime("%b %d, %Y"),
            "time_label": self._relative_time(app.applied_at),
            "initials": initials_from_name(app.applicant_name_snapshot, "JS"),
            "photo_url": photo_url,
            "status": app.status,
            "target_status": stage["target_status"],
            "can_drag": can_drag,
            "url": pu("recruiter_candidates"),
            "status_url": pu("recruiter_application_status_api", application_id=app.pk),
            "notes_url": pu("recruiter_application_notes_api", application_id=app.pk),
            "resume_url": pu("recruiter_application_resume_api", application_id=app.pk),
            "detail_url": pu("recruiter_application_detail_api", application_id=app.pk),
            "has_resume": bool(
                app.resume_file_id or (seeker and seeker.resume_file_id)
            ),
            "recruiter_notes": app.recruiter_notes or "",
            "is_terminal": ApplicationWorkflowEngine.is_terminal(app.status),
            "next_statuses": [
                {"value": s, "label": status_labels.get(s, s.replace("_", " ").title())}
                for s in next_statuses
            ],
            "detail": detail,
            "detail_json": json.dumps(detail),
        }

    def build_active_jobs(
        self,
        profile: RecruiterProfile,
        apps_qs: QuerySet,
        pu,
        filters: DashboardFilters,
    ) -> list[dict]:
        jobs = (
            JobPostingSelector()
            .for_recruiter(profile)
            .filter(status__in=(JobStatus.PUBLISHED, JobStatus.DRAFT, JobStatus.PAUSED))
            .select_related("company")
            .order_by("-published_at", "-created_at")[:6]
        )
        if filters.job_id:
            jobs = jobs.filter(pk=filters.job_id)
        if filters.department:
            jobs = jobs.filter(department__icontains=filters.department)

        status_counts = apps_qs.values("job_posting_id", "status").annotate(
            c=Count("id")
        )
        metrics: dict[str, dict[str, int]] = {}
        for row in status_counts:
            jid = str(row["job_posting_id"])
            metrics.setdefault(jid, {})
            metrics[jid][row["status"]] = row["c"]

        items = []
        now = timezone.now()
        for job in jobs:
            jid = str(job.pk)
            m = metrics.get(jid, {})
            total_apps = sum(m.values()) or job.application_count
            items.append(
                {
                    "id": jid,
                    "title": job.title,
                    "department": job.department or job.category or "General",
                    "employment_type": job.get_employment_type_display(),
                    "location": job.location
                    or job.city
                    or ("Remote" if job.is_remote else "—"),
                    "salary_range": self._salary_range(job),
                    "posted_label": (
                        timezone.localtime(job.published_at).strftime("%b %d, %Y")
                        if job.published_at
                        else timezone.localtime(job.created_at).strftime("%b %d, %Y")
                    ),
                    "deadline_label": (
                        timezone.localtime(job.application_deadline).strftime(
                            "%b %d, %Y"
                        )
                        if job.application_deadline
                        else "—"
                    ),
                    "is_expired": bool(
                        job.application_deadline and job.application_deadline < now
                    ),
                    "application_count": total_apps,
                    "shortlisted_count": m.get(JobApplicationStatus.SHORTLISTED, 0),
                    "interview_count": m.get(
                        JobApplicationStatus.INTERVIEW_SCHEDULED, 0
                    )
                    + m.get(JobApplicationStatus.INTERVIEW_COMPLETED, 0),
                    "offer_count": m.get(JobApplicationStatus.OFFER_RELEASED, 0)
                    + m.get(JobApplicationStatus.OFFER_ACCEPTED, 0),
                    "hired_count": m.get(JobApplicationStatus.HIRED, 0),
                    "status": job.status,
                    "status_label": job.get_status_display(),
                    "badges": self._job_badges(job),
                    "url": pu("recruiter_jobs"),
                    "edit_url": pu("recruiter_job_create"),
                    "publish_url": pu("recruiter_job_publish_api", job_id=job.pk),
                    "close_url": pu("recruiter_job_close_api", job_id=job.pk),
                    "pause_url": pu("recruiter_job_pause_api", job_id=job.pk),
                    "duplicate_url": pu("recruiter_job_duplicate_api", job_id=job.pk),
                    "delete_url": pu("recruiter_job_delete_api", job_id=job.pk),
                    "can_publish": job.status == JobStatus.DRAFT
                    and job.company.can_publish_jobs,
                    "can_close": job.status
                    in (JobStatus.DRAFT, JobStatus.PUBLISHED, JobStatus.PAUSED),
                    "can_pause": job.status == JobStatus.PUBLISHED,
                    "can_duplicate": True,
                    "can_delete": job.status
                    in (JobStatus.DRAFT, JobStatus.CLOSED, JobStatus.PAUSED),
                }
            )
        return items

    def build_interviews(
        self, profile: RecruiterProfile, pu, filters: DashboardFilters
    ) -> list[dict]:
        rows = self.kpi.upcoming_interviews(profile, limit=8)
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = today_start + timedelta(days=2)
        items = []
        for row in rows:
            start = timezone.localtime(row.scheduled_at)
            end_dt = row.scheduled_at + timedelta(minutes=row.duration_minutes or 45)
            end = timezone.localtime(end_dt)
            is_live = row.status == InterviewStatus.IN_PROGRESS or (
                row.scheduled_at <= now <= end_dt
            )
            within_hour = (
                row.status not in (InterviewStatus.COMPLETED, InterviewStatus.CANCELLED)
                and row.scheduled_at <= now + timedelta(hours=1)
                and end_dt >= now
            )
            if start.date() == today_start.date():
                timing = "today"
            elif start.date() == (today_start + timedelta(days=1)).date():
                timing = "tomorrow"
            else:
                timing = "upcoming"
            if row.status == InterviewStatus.COMPLETED:
                timing = "completed"
            elif row.status == InterviewStatus.CANCELLED:
                timing = "cancelled"
            elif row.status == InterviewStatus.RESCHEDULED:
                timing = "rescheduled"
            interviewer = ""
            if row.panel and isinstance(row.panel, list) and row.panel:
                first = row.panel[0]
                interviewer = (
                    first.get("name") if isinstance(first, dict) else str(first)
                )
            can_manage = row.status not in (
                InterviewStatus.COMPLETED,
                InterviewStatus.CANCELLED,
            )
            items.append(
                {
                    "id": str(row.pk),
                    "application_id": str(row.application_id),
                    "candidate_name": row.application.applicant_name_snapshot,
                    "job_title": row.application.job_title_snapshot,
                    "round_label": row.round_label or row.get_round_type_display(),
                    "interview_type": row.interview_type,
                    "mode": row.get_mode_display(),
                    "mode_key": row.mode,
                    "is_online": row.mode == InterviewMode.ONLINE,
                    "date_label": start.strftime("%b %d, %Y"),
                    "time_label": f"{start.strftime('%I:%M %p').lstrip('0')} – {end.strftime('%I:%M %p').lstrip('0')}",
                    "scheduled_at_iso": row.scheduled_at.isoformat(),
                    "duration_minutes": row.duration_minutes or 45,
                    "interviewer": interviewer or "—",
                    "meet_url": row.meet_url or "",
                    "status": row.status,
                    "status_label": row.get_status_display(),
                    "timing": timing,
                    "is_live": is_live,
                    "within_hour": within_hour,
                    "can_cancel": can_manage,
                    "can_reschedule": can_manage,
                    "cancel_url": pu(
                        "recruiter_interview_cancel_api", interview_id=row.pk
                    ),
                    "reschedule_url": pu(
                        "recruiter_interview_reschedule_api", interview_id=row.pk
                    ),
                    "initials": initials_from_name(
                        row.application.applicant_name_snapshot, "C"
                    ),
                    "interviews_url": pu("recruiter_interviews"),
                    "candidates_url": pu("recruiter_candidates"),
                    "application_detail_url": pu(
                        "recruiter_application_detail_api",
                        application_id=row.application_id,
                    ),
                }
            )
        return items

    def build_candidate_sources(
        self, apps_qs: QuerySet, filters: DashboardFilters
    ) -> dict:
        total = apps_qs.count()
        prev_month_start = timezone.now().replace(day=1) - timedelta(days=1)
        prev_month_start = prev_month_start.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        current_month_start = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        grouped = (
            apps_qs.values("source").annotate(count=Count("id")).order_by("-count")
        )
        if total == 0:
            segments = [
                {
                    "label": "EduNaukri Portal",
                    "key": "internal",
                    "pct": 0,
                    "count": 0,
                    "tone": "primary",
                    "trend": "0%",
                },
            ]
            return {"total": 0, "segments": segments}

        tones = ("primary", "secondary", "tertiary", "muted")
        segments = []
        stroke_offset = 0
        for idx, row in enumerate(grouped[:10]):
            src = row["source"] or "internal"
            label = SOURCE_LABELS.get(src, src.replace("_", " ").title())
            count = row["count"]
            pct = round((count / total) * 100)
            cur = apps_qs.filter(
                source=row["source"], applied_at__gte=current_month_start
            ).count()
            prev = apps_qs.filter(
                source=row["source"],
                applied_at__gte=prev_month_start,
                applied_at__lt=current_month_start,
            ).count()
            if prev == 0:
                trend = "+100%" if cur else "0%"
            else:
                trend = f"{round(((cur - prev) / prev) * 100):+d}%"
            segments.append(
                {
                    "label": label,
                    "key": src or "internal",
                    "pct": pct,
                    "count": count,
                    "tone": tones[idx % len(tones)],
                    "trend": trend,
                    "stroke_offset": stroke_offset,
                }
            )
            stroke_offset += pct
        return {"total": total, "segments": segments}

    def build_activity(self, apps_qs: QuerySet, pu) -> list[dict]:
        app_ids = list(apps_qs.values_list("pk", flat=True)[:200])
        if not app_ids:
            return []
        events = (
            JobApplicationTimelineEvent.objects.filter(application_id__in=app_ids)
            .select_related("application")
            .order_by("-occurred_at")[:12]
        )
        labels = {
            TimelineEventType.CREATED: "New application received",
            TimelineEventType.STATUS_CHANGED: "Status updated",
            TimelineEventType.OFFER: "Offer sent",
            TimelineEventType.HIRE: "Candidate hired",
            TimelineEventType.REJECT: "Candidate rejected",
            TimelineEventType.RECRUITER_COMMENT: "Recruiter note added",
        }
        items = []
        for ev in events:
            label = labels.get(ev.event_type, ev.get_event_type_display())
            if ev.event_type == TimelineEventType.STATUS_CHANGED and ev.to_status:
                status_label = dict(JobApplicationStatus.choices).get(
                    ev.to_status, ev.to_status
                )
                if ev.to_status == JobApplicationStatus.SHORTLISTED:
                    label = "Candidate shortlisted"
                elif ev.to_status == JobApplicationStatus.INTERVIEW_SCHEDULED:
                    label = "Interview scheduled"
                elif ev.to_status == JobApplicationStatus.HIRED:
                    label = "Candidate hired"
                elif ev.to_status == JobApplicationStatus.OFFER_RELEASED:
                    label = "Offer sent"
                else:
                    label = f"Moved to {status_label}"
            items.append(
                {
                    "id": str(ev.pk),
                    "label": label,
                    "candidate": ev.application.applicant_name_snapshot,
                    "job_title": ev.application.job_title_snapshot,
                    "timestamp": timezone.localtime(ev.occurred_at).strftime(
                        "%b %d · %I:%M %p"
                    ),
                    "url": pu("recruiter_candidates"),
                }
            )
        return items

    def build_notifications(self, profile: RecruiterProfile, pu) -> list[dict]:
        rows = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            is_deleted=False,
        ).order_by("-created_at")[:6]
        return [
            {
                "id": str(row.pk),
                "title": row.title,
                "body": row.body,
                "is_read": row.is_read,
                "timestamp": timezone.localtime(row.created_at).strftime(
                    "%b %d · %I:%M %p"
                ),
                "url": pu("recruiter_notifications"),
            }
            for row in rows
        ]

    def build_analytics(
        self,
        apps_qs: QuerySet,
        jobs_qs: QuerySet,
        profile: RecruiterProfile | None = None,
        period=None,
    ) -> dict:
        if profile is not None:
            from apps.it_recruitment.services.recruiter_analytics_section_service import (
                AnalyticsPeriod,
                RecruiterAnalyticsSectionService,
            )

            if period is None:
                period = AnalyticsPeriod(
                    "7d",
                    "Last 7 Days",
                    timezone.localdate() - timedelta(days=6),
                    timezone.localdate(),
                )
            elif isinstance(period, str):
                req = type("R", (), {"GET": {"analytics_period": period}})()
                period = AnalyticsPeriod.from_request(req)
            return RecruiterAnalyticsSectionService().build(profile, period)

        return (
            RecruiterAnalyticsSectionService().build(profile, period) if profile else {}
        )

    def build_filter_options(
        self, profile: RecruiterProfile, apps_qs: QuerySet
    ) -> dict:
        jobs = [
            {"id": str(j.pk), "title": j.title}
            for j in JobPostingSelector()
            .for_recruiter(profile)
            .only("pk", "title")[:30]
        ]
        departments = list(
            apps_qs.exclude(job_posting__department="")
            .values_list("job_posting__department", flat=True)
            .distinct()[:20]
        )
        locations = list(
            apps_qs.exclude(current_location="")
            .values_list("current_location", flat=True)
            .distinct()[:20]
        )
        return {"jobs": jobs, "departments": departments, "locations": locations}

    @staticmethod
    def _salary_range(job: JobPosting) -> str:
        if job.salary_min and job.salary_max:
            return f"₹{int(job.salary_min):,} – ₹{int(job.salary_max):,}"
        if job.salary_min:
            return f"From ₹{int(job.salary_min):,}"
        if job.salary_max:
            return f"Up to ₹{int(job.salary_max):,}"
        return ""

    @staticmethod
    def _job_badges(job: JobPosting) -> list[str]:
        badges = []
        if job.is_urgent:
            badges.append("urgent")
        if job.is_featured:
            badges.append("featured")
        if job.published_at and (timezone.now() - job.published_at).days <= 7:
            badges.append("new")
        if job.is_remote or job.work_mode == WorkMode.REMOTE:
            badges.append("remote")
        elif job.work_mode == WorkMode.HYBRID:
            badges.append("hybrid")
        else:
            badges.append("onsite")
        return badges

    @staticmethod
    def _relative_time(dt) -> str:
        if not dt:
            return "—"
        delta = timezone.now() - timezone.localtime(dt)
        if delta < timedelta(hours=48):
            return timesince(dt, timezone.now()) + " ago"
        return timezone.localtime(dt).strftime("%b %d")
