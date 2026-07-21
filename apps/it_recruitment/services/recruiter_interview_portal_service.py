"""Recruiter interview management portal — enterprise ATS interviews module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.interview_enums import (
    InterviewMode,
    InterviewRoundType,
    InterviewStatus,
)
from apps.applications.models import JobApplication
from apps.applications.models.interview import JobApplicationInterview
from apps.applications.workflow.engine import ApplicationWorkflowEngine
from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    initials_from_name,
    media_url,
)
from apps.it_recruitment.services.recruiter_dashboard_kpi_service import (
    RecruiterDashboardKPIService,
)
from apps.jobs.models import JobSeekerSkill
from apps.jobs.selectors.job_selector import JobPostingSelector


@dataclass
class RecruiterInterviewsPortalContext:
    interviews: list[dict]
    summary: list[dict]
    interviews_today: int
    schedule_candidates: list[dict]
    pipeline_stages: list[dict]
    job_filters: list[dict]
    round_options: list[dict]
    type_options: list[dict]
    status_options: list[dict]
    filters: dict
    pagination: dict
    api_urls: dict
    calendar_events: list[dict]


class RecruiterInterviewPortalService(BaseService):
    PER_PAGE = 15

    PIPELINE_STAGES = [
        {"key": JobApplicationStatus.APPLIED, "label": "Applied"},
        {"key": JobApplicationStatus.UNDER_REVIEW, "label": "Screening"},
        {"key": JobApplicationStatus.SHORTLISTED, "label": "Shortlisted"},
        {
            "key": JobApplicationStatus.INTERVIEW_SCHEDULED,
            "label": "Interview Scheduled",
        },
        {"key": "hr_interview", "label": "HR Interview"},
        {"key": "technical_interview", "label": "Technical Interview"},
        {"key": "manager_interview", "label": "Manager Interview"},
        {"key": "final_interview", "label": "Final Interview"},
        {"key": JobApplicationStatus.OFFER_RELEASED, "label": "Offer"},
        {"key": JobApplicationStatus.HIRED, "label": "Hired"},
        {"key": JobApplicationStatus.REJECTED, "label": "Rejected"},
    ]

    ROUND_OPTIONS = [
        {"value": InterviewRoundType.HR, "label": "HR Round"},
        {"value": InterviewRoundType.TECHNICAL, "label": "Technical Round"},
        {"value": InterviewRoundType.MANAGERIAL, "label": "Manager Round"},
        {"value": InterviewRoundType.FINAL, "label": "Final Round"},
        {"value": InterviewRoundType.OTHER, "label": "Custom Round"},
    ]

    TYPE_OPTIONS = [
        {"value": "video", "label": "Video Call", "mode": InterviewMode.ONLINE},
        {"value": "phone", "label": "Phone Call", "mode": InterviewMode.PHONE},
        {"value": "walkin", "label": "Walk-in", "mode": InterviewMode.OFFLINE},
        {"value": "google_meet", "label": "Google Meet", "mode": InterviewMode.ONLINE},
        {"value": "teams", "label": "Microsoft Teams", "mode": InterviewMode.ONLINE},
        {"value": "zoom", "label": "Zoom", "mode": InterviewMode.ONLINE},
        {"value": "custom", "label": "Custom", "mode": InterviewMode.ONLINE},
    ]

    SCHEDULE_ELIGIBLE_STATUSES = (
        JobApplicationStatus.SHORTLISTED,
        JobApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplicationStatus.INTERVIEW_COMPLETED,
    )

    def build(
        self,
        profile: RecruiterProfile,
        *,
        when: str = "",
        q: str = "",
        status: str = "",
        job_id: str = "",
        mode: str = "",
        date_from: str = "",
        date_to: str = "",
        page: int = 1,
    ) -> RecruiterInterviewsPortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        qs = self._interview_queryset(profile)
        qs = self._apply_filters(
            qs,
            when=when,
            q=q,
            status=status,
            job_id=job_id,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
        )

        stats = self._compute_stats(profile, qs)
        paginator = Paginator(qs, self.PER_PAGE)
        page_obj = paginator.get_page(page)
        interviews = [self._serialize(row, pu) for row in page_obj.object_list]

        job_filters = [
            {"id": str(j.pk), "title": j.title}
            for j in JobPostingSelector()
            .for_recruiter(profile)[:50]
        ]

        return RecruiterInterviewsPortalContext(
            interviews=interviews,
            interviews_today=stats["today"],
            summary=stats["summary"],
            schedule_candidates=self._schedule_candidates(profile, pu),
            pipeline_stages=self.PIPELINE_STAGES,
            job_filters=job_filters,
            round_options=self.ROUND_OPTIONS,
            type_options=self.TYPE_OPTIONS,
            status_options=[
                {"value": s.value, "label": s.label} for s in InterviewStatus
            ]
            + [
                {"value": "upcoming", "label": "Upcoming"},
                {"value": "no_show", "label": "No Show"},
            ],
            filters={
                "when": when,
                "q": q,
                "status": status,
                "job_id": job_id,
                "mode": mode,
                "date_from": date_from,
                "date_to": date_to,
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
            calendar_events=[self._calendar_event(i) for i in interviews],
            api_urls=self._api_urls(pu),
        )

    def build_list_payload(self, profile: RecruiterProfile, **filters) -> dict:
        ctx = self.build(profile, **filters)
        return {
            "success": True,
            "interviews": ctx.interviews,
            "summary": ctx.summary,
            "pagination": ctx.pagination,
            "calendar_events": ctx.calendar_events,
        }

    @staticmethod
    def _api_urls(pu) -> dict:
        placeholder_iv = "00000000-0000-0000-0000-000000000000"
        placeholder_app = "00000000-0000-0000-0000-000000000000"
        return {
            "list": pu("recruiter_interviews_list_api"),
            "schedule": pu(
                "recruiter_interview_schedule_api", application_id=placeholder_app
            ),
            "schedule_candidates": pu("recruiter_interview_schedule_candidates_api"),
            "cancel_template": pu(
                "recruiter_interview_cancel_api", interview_id=placeholder_iv
            ),
            "reschedule_template": pu(
                "recruiter_interview_reschedule_api", interview_id=placeholder_iv
            ),
            "feedback_template": pu(
                "recruiter_interview_feedback_api", interview_id=placeholder_iv
            ),
            "status_template": pu(
                "recruiter_interview_status_api", interview_id=placeholder_iv
            ),
            "detail_template": pu(
                "recruiter_application_detail_api", application_id=placeholder_app
            ),
            "application_status_template": pu(
                "recruiter_application_status_api", application_id=placeholder_app
            ),
            "resume_template": pu(
                "recruiter_application_resume_api", application_id=placeholder_app
            ),
            "candidates_url": pu("recruiter_candidates"),
        }

    def _interview_queryset(self, profile: RecruiterProfile):
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        return (
            JobApplicationInterview.objects.filter(
                application__job_posting__company_id__in=company_ids,
                application__is_deleted=False,
                is_deleted=False,
            )
            .select_related(
                "application",
                "application__job_posting",
                "application__job_posting__company",
                "application__job_seeker",
                "application__job_seeker__profile_photo",
                "application__job_seeker__user",
            )
            .order_by("-scheduled_at")
        )

    @staticmethod
    def _apply_filters(qs, *, when, q, status, job_id, mode, date_from, date_to):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if when == "today":
            qs = qs.filter(
                scheduled_at__gte=today_start,
                scheduled_at__lt=today_start + timedelta(days=1),
            )
        elif when == "upcoming":
            qs = qs.filter(
                scheduled_at__gte=now,
                status__in=(
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.RESCHEDULED,
                ),
            )
        elif when == "completed":
            qs = qs.filter(status=InterviewStatus.COMPLETED)
        elif when == "cancelled":
            qs = qs.filter(status=InterviewStatus.CANCELLED)
        if q:
            qs = qs.filter(
                Q(application__applicant_name_snapshot__icontains=q)
                | Q(application__job_title_snapshot__icontains=q)
                | Q(round_label__icontains=q)
                | Q(instructions__icontains=q)
            )
        if status and status not in ("upcoming", "no_show"):
            qs = qs.filter(status=status)
        elif status == "upcoming":
            qs = qs.filter(
                scheduled_at__gte=now,
                status__in=(
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.RESCHEDULED,
                ),
            )
        elif status == "no_show":
            qs = qs.filter(feedback__decision="no_show")
        if job_id:
            qs = qs.filter(application__job_posting_id=job_id)
        if mode:
            qs = qs.filter(mode=mode)
        if date_from:
            qs = qs.filter(scheduled_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(scheduled_at__date__lte=date_to)
        return qs

    def _compute_stats(self, profile, filtered_qs) -> dict:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        base = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
        )
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = RecruiterDashboardKPIService().interviews_today_count(profile)
        upcoming = base.filter(
            scheduled_at__gte=now,
            status__in=(
                InterviewStatus.SCHEDULED,
                InterviewStatus.CONFIRMED,
                InterviewStatus.RESCHEDULED,
            ),
        ).count()
        completed = base.filter(status=InterviewStatus.COMPLETED).count()
        cancelled = base.filter(status=InterviewStatus.CANCELLED).count()
        apps = JobApplication.objects.filter(
            job_posting__company_id__in=company_ids,
            is_deleted=False,
        )
        offers = apps.filter(status=JobApplicationStatus.OFFER_RELEASED).count()
        hired = apps.filter(status=JobApplicationStatus.HIRED).count()
        success = round((hired / completed) * 100, 1) if completed else 0

        return {
            "today": today_count,
            "summary": [
                {
                    "key": "upcoming",
                    "label": "Upcoming",
                    "value": upcoming,
                    "icon": "calendar_today",
                    "tone": "primary",
                },
                {
                    "key": "today",
                    "label": "Today",
                    "value": today_count,
                    "icon": "alarm",
                    "tone": "secondary",
                },
                {
                    "key": "completed",
                    "label": "Completed",
                    "value": completed,
                    "icon": "check_circle",
                    "tone": "tertiary",
                },
                {
                    "key": "cancelled",
                    "label": "Cancelled",
                    "value": cancelled,
                    "icon": "cancel",
                    "tone": "muted",
                },
                {
                    "key": "offers",
                    "label": "Offers Sent",
                    "value": offers,
                    "icon": "mail",
                    "tone": "primary",
                },
                {
                    "key": "hired",
                    "label": "Hires",
                    "value": hired,
                    "icon": "emoji_events",
                    "tone": "tertiary",
                },
                {
                    "key": "success_rate",
                    "label": "Success Rate",
                    "value": f"{success}%",
                    "icon": "trending_up",
                    "tone": "secondary",
                },
            ],
        }

    def _schedule_candidates(self, profile: RecruiterProfile, pu) -> list[dict]:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        apps = (
            JobApplication.objects.filter(
                job_posting__company_id__in=company_ids,
                is_deleted=False,
                status__in=self.SCHEDULE_ELIGIBLE_STATUSES,
            )
            .select_related(
                "job_seeker",
                "job_seeker__profile_photo",
                "job_seeker__user",
                "job_posting",
                "job_posting__company",
            )
            .prefetch_related(
                Prefetch(
                    "job_seeker__skills",
                    queryset=JobSeekerSkill.objects.select_related("skill").filter(
                        is_deleted=False
                    ),
                )
            )
            .order_by("-applied_at")[:30]
        )
        items = []
        for app in apps:
            seeker = app.job_seeker
            skills = [
                link.skill.name
                for link in seeker.skills.all()
                if getattr(link, "skill", None)
            ][:8]
            items.append(
                {
                    "application_id": str(app.pk),
                    "candidate_name": app.applicant_name_snapshot,
                    "job_title": app.job_title_snapshot,
                    "company_name": app.company_name_snapshot
                    or app.job_posting.company.name,
                    "experience_years": seeker.experience_years
                    if seeker and seeker.experience_years is not None
                    else "—",
                    "skills_label": ", ".join(skills[:5]) if skills else "—",
                    "status": app.status,
                    "status_label": app.get_status_display(),
                    "photo_url": media_url(seeker.profile_photo)
                    if seeker and seeker.profile_photo_id
                    else "",
                    "initials": initials_from_name(app.applicant_name_snapshot, "C"),
                    "has_resume": bool(
                        app.resume_file_id or getattr(seeker, "resume_file_id", None)
                    ),
                    "resume_preview_url": pu(
                        "recruiter_application_resume_api", application_id=app.pk
                    )
                    + "?preview=1",
                    "resume_url": pu(
                        "recruiter_application_resume_api", application_id=app.pk
                    ),
                    "schedule_url": pu(
                        "recruiter_interview_schedule_api", application_id=app.pk
                    ),
                }
            )
        return items

    def _serialize(self, row: JobApplicationInterview, pu) -> dict:
        app = row.application
        seeker = app.job_seeker
        start = timezone.localtime(row.scheduled_at)
        end_dt = row.scheduled_at + timedelta(minutes=row.duration_minutes or 45)
        end = timezone.localtime(end_dt)
        now = timezone.now()
        is_upcoming = row.scheduled_at >= now and row.status in (
            InterviewStatus.SCHEDULED,
            InterviewStatus.CONFIRMED,
            InterviewStatus.RESCHEDULED,
        )
        is_live = row.status == InterviewStatus.IN_PROGRESS or (
            row.scheduled_at <= now <= end_dt
            and row.status not in (InterviewStatus.COMPLETED, InterviewStatus.CANCELLED)
        )
        interviewer = self._panel_name(row.panel)
        feedback = row.feedback or {}
        display_status = row.get_status_display()
        if feedback.get("decision") == "no_show":
            display_status = "No Show"
        elif is_upcoming and row.status == InterviewStatus.SCHEDULED:
            display_status = "Upcoming"

        can_manage = row.status not in (
            InterviewStatus.COMPLETED,
            InterviewStatus.CANCELLED,
        )
        pipeline_index = self._pipeline_index(app.status, row.round_type)

        return {
            "id": str(row.pk),
            "application_id": str(row.application_id),
            "candidate_name": app.applicant_name_snapshot,
            "job_title": app.job_title_snapshot,
            "company_name": app.company_name_snapshot or app.job_posting.company.name,
            "title": row.round_label or row.interview_type,
            "round_type": row.round_type,
            "round_label": row.round_label or row.get_round_type_display(),
            "interview_type": row.interview_type,
            "mode": row.mode,
            "mode_label": row.get_mode_display(),
            "date_label": start.strftime("%b %d, %Y"),
            "time_label": f"{start.strftime('%I:%M %p').lstrip('0')} – {end.strftime('%I:%M %p').lstrip('0')}",
            "scheduled_at_iso": row.scheduled_at.isoformat(),
            "duration_minutes": row.duration_minutes or 45,
            "interviewer": interviewer or "—",
            "meet_url": row.meet_url or "",
            "location": row.location or "",
            "instructions": row.instructions or "",
            "status": row.status,
            "status_label": display_status,
            "status_tone": self._status_tone(row.status, feedback),
            "application_status": app.status,
            "application_status_label": app.get_status_display(),
            "stage_label": app.get_status_display(),
            "initials": initials_from_name(app.applicant_name_snapshot, "C"),
            "photo_url": media_url(seeker.profile_photo)
            if seeker and seeker.profile_photo_id
            else "",
            "is_upcoming": is_upcoming,
            "is_live": is_live,
            "has_resume": bool(
                app.resume_file_id or getattr(seeker, "resume_file_id", None)
            ),
            "resume_url": pu("recruiter_application_resume_api", application_id=app.pk),
            "resume_preview_url": pu(
                "recruiter_application_resume_api", application_id=app.pk
            )
            + "?preview=1",
            "can_cancel": can_manage,
            "can_reschedule": can_manage,
            "can_complete": row.status
            not in (InterviewStatus.COMPLETED, InterviewStatus.CANCELLED),
            "cancel_url": pu("recruiter_interview_cancel_api", interview_id=row.pk),
            "reschedule_url": pu(
                "recruiter_interview_reschedule_api", interview_id=row.pk
            ),
            "feedback_url": pu("recruiter_interview_feedback_api", interview_id=row.pk),
            "status_url": pu("recruiter_interview_status_api", interview_id=row.pk),
            "detail_url": pu("recruiter_application_detail_api", application_id=app.pk),
            "application_status_url": pu(
                "recruiter_application_status_api", application_id=app.pk
            ),
            "candidates_url": pu("recruiter_candidates"),
            "email": getattr(seeker.user, "email", "") if seeker else "",
            "phone": seeker.phone if seeker else "",
            "pipeline_index": pipeline_index,
            "pipeline_total": len(self.PIPELINE_STAGES),
            "feedback": feedback,
            "next_statuses": [
                {
                    "value": s,
                    "label": dict(JobApplicationStatus.choices).get(
                        s, s.replace("_", " ").title()
                    ),
                }
                for s in sorted(
                    ApplicationWorkflowEngine.transitions.get(app.status, set())
                )
            ],
        }

    @staticmethod
    def _panel_name(panel) -> str:
        if panel and isinstance(panel, list) and panel:
            first = panel[0]
            return first.get("name") if isinstance(first, dict) else str(first)
        return ""

    @staticmethod
    def _status_tone(status: str, feedback: dict) -> str:
        if feedback.get("decision") == "no_show":
            return "danger"
        tones = {
            InterviewStatus.SCHEDULED: "primary",
            InterviewStatus.CONFIRMED: "primary",
            InterviewStatus.IN_PROGRESS: "warning",
            InterviewStatus.COMPLETED: "success",
            InterviewStatus.CANCELLED: "danger",
            InterviewStatus.RESCHEDULED: "warning",
        }
        return tones.get(status, "muted")

    def _pipeline_index(self, app_status: str, round_type: str) -> int:
        round_map = {
            InterviewRoundType.HR: 4,
            InterviewRoundType.TECHNICAL: 5,
            InterviewRoundType.MANAGERIAL: 6,
            InterviewRoundType.FINAL: 7,
        }
        if app_status == JobApplicationStatus.HIRED:
            return 9
        if app_status == JobApplicationStatus.REJECTED:
            return 10
        if app_status == JobApplicationStatus.OFFER_RELEASED:
            return 8
        if (
            app_status == JobApplicationStatus.INTERVIEW_SCHEDULED
            and round_type in round_map
        ):
            return round_map[round_type]
        status_index = {
            JobApplicationStatus.APPLIED: 0,
            JobApplicationStatus.UNDER_REVIEW: 1,
            JobApplicationStatus.SHORTLISTED: 2,
            JobApplicationStatus.INTERVIEW_SCHEDULED: 3,
            JobApplicationStatus.INTERVIEW_COMPLETED: 7,
        }
        return status_index.get(app_status, 3)

    @staticmethod
    def _calendar_event(item: dict) -> dict:
        return {
            "id": item["id"],
            "title": f"{item['candidate_name']} — {item['round_label']}",
            "start": item["scheduled_at_iso"],
            "url": f"#interview-{item['id']}",
        }

    @staticmethod
    def whatsapp_message(item: dict) -> str:
        link_or_addr = item.get("meet_url") or item.get("location") or "TBD"
        return (
            f"Hello {item.get('candidate_name', 'Candidate')},\n\n"
            f"Your interview for the position of {item.get('job_title', '')} at "
            f"{item.get('company_name', 'our company')} has been scheduled.\n\n"
            f"Interview: {item.get('round_label', '')} ({item.get('mode_label', '')})\n"
            f"Date: {item.get('date_label', '')}\n"
            f"Time: {item.get('time_label', '')}\n"
            f"Interviewer: {item.get('interviewer', 'TBD')}\n"
            f"Meeting Link / Address: {link_or_addr}\n\n"
            f"Please join on time.\n\nThank you,\n{item.get('company_name', 'Recruitment Team')}"
        )
