"""Job seeker application tracking portal — list, detail, analytics, and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.applications.constants.enums import (
    TERMINAL_STATUSES,
    JobApplicationStatus,
    TimelineEventType,
)
from apps.applications.models import JobApplication
from apps.applications.selectors.application_selector import JobApplicationSelector
from apps.applications.selectors.timeline_selector import JobApplicationTimelineSelector
from apps.applications.services.application_statistics_service import (
    ApplicationStatisticsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_matching_service import JobMatchingService
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    media_url,
)
from apps.reports.selectors.featured_jobs import FeaturedJobsSelector
from apps.applications.services.joining_status_resolver import JoiningStatusResolver

WITHDRAW_ALLOWED_STATUSES = frozenset(
    {
        JobApplicationStatus.APPLIED,
        JobApplicationStatus.UNDER_REVIEW,
        JobApplicationStatus.SHORTLISTED,
    }
)

OFFER_ACTION_STATUSES = frozenset({JobApplicationStatus.OFFER_RELEASED})

OFFER_VISIBLE_STATUSES = frozenset({
    JobApplicationStatus.OFFER_RELEASED,
    JobApplicationStatus.OFFER_ACCEPTED,
    JobApplicationStatus.OFFER_DECLINED,
    JobApplicationStatus.JOINING_IN_PROGRESS,
    JobApplicationStatus.HIRED,
    JobApplicationStatus.SELECTED,
    JobApplicationStatus.JOINED,
})

STATUS_UI: dict[str, dict] = {
    JobApplicationStatus.APPLIED: {
        "label": "Applied",
        "badge": "jsd-app-badge--applied",
        "icon": "bi-send-check",
        "description": "Your application was submitted successfully.",
    },
    JobApplicationStatus.UNDER_REVIEW: {
        "label": "Under Review",
        "badge": "jsd-app-badge--review",
        "icon": "bi-eye",
        "description": "The hiring team is reviewing your profile.",
    },
    JobApplicationStatus.SHORTLISTED: {
        "label": "Resume Shortlisted",
        "badge": "jsd-app-badge--shortlisted",
        "icon": "bi-star-fill",
        "description": "Your profile has been shortlisted for the next stage.",
    },
    JobApplicationStatus.INTERVIEW_SCHEDULED: {
        "label": "Interview Scheduled",
        "badge": "jsd-app-badge--interview",
        "icon": "bi-calendar-event",
        "description": "An interview has been scheduled.",
    },
    JobApplicationStatus.INTERVIEW_COMPLETED: {
        "label": "Interview Completed",
        "badge": "jsd-app-badge--interview",
        "icon": "bi-check2-circle",
        "description": "Your interview round is complete.",
    },
    JobApplicationStatus.OFFER_RELEASED: {
        "label": "Offer Released",
        "badge": "jsd-app-badge--offer",
        "icon": "bi-envelope-open-heart",
        "description": "An offer letter has been released for your review.",
    },
    JobApplicationStatus.OFFER_ACCEPTED: {
        "label": "Offer Accepted",
        "badge": "jsd-app-badge--offer",
        "icon": "bi-hand-thumbs-up-fill",
        "description": "You accepted the offer.",
    },
    JobApplicationStatus.OFFER_DECLINED: {
        "label": "Offer Declined",
        "badge": "jsd-app-badge--muted",
        "icon": "bi-hand-thumbs-down",
        "description": "You declined the offer.",
    },
    JobApplicationStatus.HIRED: {
        "label": "Hired",
        "badge": "jsd-app-badge--hired",
        "icon": "bi-trophy-fill",
        "description": "Congratulations — you have been hired.",
    },
    JobApplicationStatus.SELECTED: {
        "label": "Selected",
        "badge": "jsd-app-badge--hired",
        "icon": "bi-trophy-fill",
        "description": "Congratulations — you have been selected.",
    },
    JobApplicationStatus.JOINING_IN_PROGRESS: {
        "label": "Joining in Progress",
        "badge": "jsd-app-badge--hired",
        "icon": "bi-arrow-repeat",
        "description": "Your joining formalities are in progress.",
    },
    JobApplicationStatus.JOINED: {
        "label": "Joined",
        "badge": "jsd-app-badge--hired",
        "icon": "bi-trophy-fill",
        "description": "Congratulations — you have joined.",
    },
    JobApplicationStatus.REJECTED: {
        "label": "Rejected",
        "badge": "jsd-app-badge--rejected",
        "icon": "bi-x-circle-fill",
        "description": "This application was not selected.",
    },
    JobApplicationStatus.WITHDRAWN: {
        "label": "Application Withdrawn",
        "badge": "jsd-app-badge--muted",
        "icon": "bi-arrow-return-left",
        "description": "You withdrew this application.",
    },
    JobApplicationStatus.EXPIRED: {
        "label": "Position Closed",
        "badge": "jsd-app-badge--muted",
        "icon": "bi-lock-fill",
        "description": "This position is no longer accepting applications.",
    },
}


@dataclass
class ApplicationAnalyticsCard:
    key: str
    label: str
    value: int
    icon: str
    tone: str


@dataclass
class ApplicationListCard:
    id: str
    title: str
    company_name: str
    company_verified: bool
    logo_url: str | None
    logo_initial: str
    domain_label: str
    status: str
    status_label: str
    status_badge: str
    status_icon: str
    applied_date: str
    last_updated: str
    match_percent: int | None
    recruiter_name: str
    recruiter_avatar: str | None
    detail_url: str
    is_active: bool


@dataclass
class TimelineEntry:
    id: str
    title: str
    description: str
    actor_name: str
    icon: str
    tone: str
    occurred_at: str
    occurred_time: str


@dataclass
class InterviewDetails:
    interview_type: str
    date_label: str
    time_label: str
    timezone_label: str
    mode: str
    meet_url: str | None
    panel: str
    instructions: str
    countdown_label: str | None


@dataclass
class OfferDetails:
    salary_display: str
    designation: str
    joining_date: str
    expiry_label: str | None
    letter_url: str | None


@dataclass
class ApplicationDetailContext:
    application_id: str
    status: str
    status_label: str
    status_badge: str
    status_icon: str
    status_description: str
    applied_date: str
    last_updated: str
    match_percent: int | None
    cover_letter: str
    resume_filename: str | None
    resume_download_url: str | None
    can_withdraw: bool
    can_accept_offer: bool
    can_decline_offer: bool
    next_step: str
    job_title: str
    company_name: str
    company_verified: bool
    company_slug: str | None
    company_profile_url: str | None
    department: str
    salary_display: str | None
    experience_label: str | None
    location: str
    employment_type: str
    work_mode: str
    job_description: str
    job_detail_url: str
    recruiter_name: str
    recruiter_avatar: str | None
    timeline: list[TimelineEntry] = field(default_factory=list)
    interview: InterviewDetails | None = None
    offer: OfferDetails | None = None
    show_similar_jobs: bool = False


@dataclass
class ApplicationListResult:
    applications: list[ApplicationListCard]
    analytics: list[ApplicationAnalyticsCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters: dict


class JobSeekerApplicationPortalService(BaseService):
    """Read models and action helpers for the job seeker applications portal."""

    def __init__(self):
        self._selector = JobApplicationSelector()
        self._timeline = JobApplicationTimelineSelector()
        self._mapper = FeaturedJobsSelector()
        self._stats = ApplicationStatisticsService()

    def list_applications(
        self,
        profile: JobSeekerProfile,
        *,
        page: int = 1,
        page_size: int = 10,
        status: str = "",
        q: str = "",
        active_only: bool = False,
        interview_only: bool = False,
        offer_only: bool = False,
        rejected_only: bool = False,
    ) -> ApplicationListResult:
        qs = (
            self._selector.for_seeker(profile)
            .select_related(
                "job_posting",
                "job_posting__company",
                "job_posting__company__logo_file",
                "job_posting__posted_by",
                "job_posting__posted_by__profile_image",
            )
            .prefetch_related("timeline", "job_posting__required_skills__skill")
        )

        if status:
            qs = qs.filter(status=status)
        if active_only:
            qs = qs.exclude(status__in=TERMINAL_STATUSES)
        if interview_only:
            qs = qs.filter(
                status__in=[
                    JobApplicationStatus.INTERVIEW_SCHEDULED,
                    JobApplicationStatus.INTERVIEW_COMPLETED,
                ]
            )
        if offer_only:
            qs = qs.filter(
                status__in=[
                    JobApplicationStatus.OFFER_RELEASED,
                    JobApplicationStatus.OFFER_ACCEPTED,
                ]
            )
        if rejected_only:
            qs = qs.filter(status=JobApplicationStatus.REJECTED)
        if q:
            qs = qs.filter(
                Q(job_title_snapshot__icontains=q)
                | Q(company_name_snapshot__icontains=q)
                | Q(job_posting__title__icontains=q)
            )

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        match_cache = self._match_scores(
            profile,
            [app.job_posting for app in page_obj.object_list if app.job_posting_id],
        )

        cards = [
            self._map_list_card(
                app, profile, match_percent=match_cache.get(app.job_posting_id)
            )
            for app in page_obj.object_list
        ]
        summary = self._stats.seeker_dashboard(profile)
        by_status = summary.get("applications_by_status", {})

        return ApplicationListResult(
            applications=cards,
            analytics=self._analytics_cards(
                by_status, summary.get("active_applications", 0)
            ),
            total_count=paginator.count,
            page=page_obj.number,
            page_size=page_size,
            total_pages=paginator.num_pages,
            filters={
                "status": status,
                "q": q,
                "active_only": active_only,
                "interview_only": interview_only,
                "offer_only": offer_only,
                "rejected_only": rejected_only,
            },
        )

    def get_detail(
        self, profile: JobSeekerProfile, application_id
    ) -> ApplicationDetailContext | None:
        app = (
            self._selector.for_seeker(profile)
            .filter(pk=application_id)
            .select_related(
                "job_posting",
                "job_posting__company",
                "job_posting__posted_by",
                "job_posting__posted_by__profile_image",
                "resume_file",
            )
            .first()
        )
        if not app:
            return None
        return self._map_detail(app, profile)

    @staticmethod
    def can_withdraw(application: JobApplication) -> bool:
        return application.status in WITHDRAW_ALLOWED_STATUSES

    @staticmethod
    def can_respond_to_offer(application: JobApplication) -> bool:
        return application.status in OFFER_ACTION_STATUSES

    def _map_list_card(
        self,
        app: JobApplication,
        profile: JobSeekerProfile,
        *,
        match_percent: int | None,
    ) -> ApplicationListCard:
        job = app.job_posting
        company = job.company if job else None
        ui = STATUS_UI.get(app.status, STATUS_UI[JobApplicationStatus.APPLIED])
        org_name = app.company_name_snapshot or (company.name if company else "")
        recruiter = job.posted_by if job else None
        pu = lambda name, **kw: PortalURLService.jobseeker(profile.user, name, **kw)

        return ApplicationListCard(
            id=str(app.pk),
            title=app.job_title_snapshot or (job.title if job else ""),
            company_name=org_name,
            company_verified=True,
            logo_url=media_url(company.logo_file)
            if company and company.logo_file
            else None,
            logo_initial=(org_name[:1] or "E").upper(),
            domain_label="IT Domain",
            status=app.status,
            status_label=ui["label"],
            status_badge=ui["badge"],
            status_icon=ui["icon"],
            applied_date=timezone.localtime(app.applied_at).strftime("%b %d, %Y"),
            last_updated=timezone.localtime(app.status_changed_at).strftime(
                "%b %d, %Y"
            ),
            match_percent=match_percent,
            recruiter_name=recruiter.full_name if recruiter else "Recruiting Team",
            recruiter_avatar=media_url(recruiter.profile_image)
            if recruiter and recruiter.profile_image
            else None,
            detail_url=pu("jobseeker_application_detail", application_id=app.pk),
            is_active=app.status not in TERMINAL_STATUSES,
        )

    def _map_detail(
        self, app: JobApplication, profile: JobSeekerProfile
    ) -> ApplicationDetailContext:
        job = app.job_posting
        company = job.company if job else None
        ui = STATUS_UI.get(app.status, STATUS_UI[JobApplicationStatus.APPLIED])
        recruiter = job.posted_by if job else None
        org_name = app.company_name_snapshot or (company.name if company else "")
        if job:
            if job.is_remote:
                location = "Remote"
            elif job.location:
                location = job.location
            else:
                location_parts = [part for part in (job.city, job.state) if part]
                location = ", ".join(location_parts)
        else:
            location = ""
        timeline_events = list(
            self._timeline.for_application(app).order_by("occurred_at")
        )
        interview = self._extract_interview(app, timeline_events)
        offer = self._extract_offer(app, timeline_events)

        resume_name = None
        if app.resume_snapshot:
            resume_name = app.resume_snapshot.get("original_filename")
        elif app.resume_file:
            resume_name = app.resume_file.original_filename

        company_slug = company.slug if company else None
        pu = lambda name, **kw: PortalURLService.jobseeker(profile.user, name, **kw)
        company_profile_url = (
            reverse("institution_detail", kwargs={"slug": company_slug})
            if company_slug
            else None
        )

        return ApplicationDetailContext(
            application_id=str(app.pk),
            status=app.status,
            status_label=ui["label"],
            status_badge=ui["badge"],
            status_icon=ui["icon"],
            status_description=ui["description"],
            applied_date=timezone.localtime(app.applied_at).strftime(
                "%b %d, %Y · %I:%M %p"
            ),
            last_updated=timezone.localtime(app.status_changed_at).strftime(
                "%b %d, %Y · %I:%M %p"
            ),
            match_percent=self._match_score(profile, job) if job else None,
            cover_letter=app.cover_letter or "",
            resume_filename=resume_name,
            resume_download_url=(
                pu("jobseeker_profile_resume_download") if app.resume_file_id else None
            ),
            can_withdraw=self.can_withdraw(app),
            can_accept_offer=self.can_respond_to_offer(app),
            can_decline_offer=self.can_respond_to_offer(app),
            next_step=self._next_step(app.status),
            job_title=app.job_title_snapshot or (job.title if job else ""),
            company_name=org_name,
            company_verified=True,
            company_slug=company_slug,
            company_profile_url=company_profile_url,
            department=job.department if job else "",
            salary_display=(
                self._mapper._salary(
                    job.salary_min, job.salary_max, job.salary_visibility
                )
                if job
                else None
            ),
            experience_label=self._mapper._experience(job.experience_min)
            if job
            else None,
            location=location,
            employment_type=job.get_employment_type_display() if job else "",
            work_mode=job.get_work_mode_display() if job else "",
            job_description=job.description if job else "",
            job_detail_url=reverse("marketplace_job_detail", kwargs={"job_id": job.pk})
            if job
            else "#",
            recruiter_name=recruiter.full_name if recruiter else "Recruiting Team",
            recruiter_avatar=media_url(recruiter.profile_image)
            if recruiter and recruiter.profile_image
            else None,
            timeline=self._map_timeline(timeline_events, recruiter),
            interview=interview,
            offer=offer,
            show_similar_jobs=app.status == JobApplicationStatus.REJECTED,
        )

    def _map_timeline(self, events, recruiter) -> list[TimelineEntry]:
        entries: list[TimelineEntry] = []
        for event in reversed(events):
            ui = self._timeline_ui(event)
            actor = (
                "You"
                if event.event_type == TimelineEventType.WITHDRAW
                else (recruiter.full_name if recruiter else "Recruiting Team")
            )
            when = timezone.localtime(event.occurred_at)
            entries.append(
                TimelineEntry(
                    id=str(event.pk),
                    title=ui["title"],
                    description=event.notes or ui["description"],
                    actor_name=actor,
                    icon=ui["icon"],
                    tone=ui["tone"],
                    occurred_at=when.strftime("%b %d, %Y"),
                    occurred_time=when.strftime("%I:%M %p"),
                )
            )
        return entries

    @staticmethod
    def _timeline_ui(event) -> dict:
        if event.event_type == TimelineEventType.CREATED:
            return {
                "title": "Applied Successfully",
                "icon": "bi-send-check",
                "tone": "success",
                "description": "",
            }
        if event.event_type == TimelineEventType.WITHDRAW:
            return {
                "title": "Application Withdrawn",
                "icon": "bi-arrow-return-left",
                "tone": "muted",
                "description": "",
            }
        if event.event_type == TimelineEventType.HIRE:
            return {
                "title": "Hired",
                "icon": "bi-trophy-fill",
                "tone": "success",
                "description": "",
            }
        if event.event_type == TimelineEventType.REJECT:
            return {
                "title": "Application Rejected",
                "icon": "bi-x-circle",
                "tone": "danger",
                "description": "",
            }
        if event.event_type == TimelineEventType.OFFER:
            return {
                "title": "Offer Update",
                "icon": "bi-envelope-open-heart",
                "tone": "offer",
                "description": "",
            }
        if event.event_type == TimelineEventType.RECRUITER_COMMENT:
            return {
                "title": "Recruiter Update",
                "icon": "bi-chat-left-text",
                "tone": "info",
                "description": "",
            }
        if event.to_status == JobApplicationStatus.INTERVIEW_SCHEDULED:
            return {
                "title": "Interview Scheduled",
                "icon": "bi-calendar-event",
                "tone": "interview",
                "description": "",
            }
        if event.to_status == JobApplicationStatus.SHORTLISTED:
            return {
                "title": "Profile Shortlisted",
                "icon": "bi-star-fill",
                "tone": "success",
                "description": "",
            }
        if event.to_status == JobApplicationStatus.UNDER_REVIEW:
            return {
                "title": "Profile Under Review",
                "icon": "bi-eye",
                "tone": "info",
                "description": "",
            }
        return {
            "title": "Status Updated",
            "icon": "bi-arrow-repeat",
            "tone": "info",
            "description": "",
        }

    def _extract_interview(
        self, app: JobApplication, events
    ) -> InterviewDetails | None:
        if app.status not in (
            JobApplicationStatus.INTERVIEW_SCHEDULED,
            JobApplicationStatus.INTERVIEW_COMPLETED,
            JobApplicationStatus.OFFER_RELEASED,
            JobApplicationStatus.OFFER_ACCEPTED,
            JobApplicationStatus.HIRED,
        ):
            return None
        meta = {}
        for event in events:
            if (
                event.to_status == JobApplicationStatus.INTERVIEW_SCHEDULED
                and event.metadata
            ):
                meta = event.metadata
                break
        scheduled_at = meta.get("scheduled_at") or app.status_changed_at
        when = timezone.localtime(
            datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            if isinstance(scheduled_at, str)
            else scheduled_at
        )
        countdown = None
        if (
            app.status == JobApplicationStatus.INTERVIEW_SCHEDULED
            and when > timezone.localtime()
        ):
            delta = when - timezone.localtime()
            days = delta.days
            hours = delta.seconds // 3600
            countdown = f"{days}d {hours}h remaining" if days else f"{hours}h remaining"

        return InterviewDetails(
            interview_type=meta.get("interview_type", "Technical Interview"),
            date_label=when.strftime("%A, %b %d, %Y"),
            time_label=when.strftime("%I:%M %p"),
            timezone_label=meta.get("timezone", "IST"),
            mode=meta.get("mode", meta.get("interview_mode", "Video Call")),
            meet_url=meta.get("meet_url") or meta.get("meeting_link"),
            panel=meta.get("panel", meta.get("interviewers", "Hiring Panel")),
            instructions=meta.get(
                "instructions", "Please join 5 minutes early with a stable connection."
            ),
            countdown_label=countdown,
        )

    def _extract_offer(self, app: JobApplication, events) -> OfferDetails | None:
        if app.status not in OFFER_VISIBLE_STATUSES:
            return None
        meta = {}
        for event in reversed(events):
            if event.event_type == TimelineEventType.OFFER and event.metadata:
                meta = event.metadata
                break
        job = app.job_posting
        salary = meta.get("offered_salary") or meta.get("salary")
        if salary is None and job:
            salary = format_salary_lpa(
                job.salary_min, job.salary_max, job.salary_currency
            )
        elif salary is not None and job:
            salary = str(salary)
        expiry = meta.get("offer_expiry") or meta.get("expires_at")
        expiry_label = None
        if expiry:
            try:
                exp = timezone.localtime(
                    datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
                    if isinstance(expiry, str)
                    else expiry
                )
                expiry_label = exp.strftime("%b %d, %Y")
            except (TypeError, ValueError):
                expiry_label = str(expiry)

        # ── Centralized joining status (single source of truth) ──
        joining_label, joining_date_str = JoiningStatusResolver.resolve_it(
            app, offer_meta=meta
        )
        joining_display = JoiningStatusResolver.joining_display(joining_label, joining_date_str)

        return OfferDetails(
            salary_display=salary or "As discussed",
            designation=meta.get("designation", job.title if job else ""),
            joining_date=joining_display,
            expiry_label=expiry_label,
            letter_url=meta.get("offer_letter_url") or meta.get("letter_url"),
        )

    @staticmethod
    def _next_step(status: str) -> str:
        mapping = {
            JobApplicationStatus.APPLIED: "Recruiter review",
            JobApplicationStatus.UNDER_REVIEW: "Shortlisting decision",
            JobApplicationStatus.SHORTLISTED: "Interview scheduling",
            JobApplicationStatus.INTERVIEW_SCHEDULED: "Interview completion",
            JobApplicationStatus.INTERVIEW_COMPLETED: "Final evaluation",
            JobApplicationStatus.OFFER_RELEASED: "Review and respond to offer",
            JobApplicationStatus.OFFER_ACCEPTED: "Onboarding preparation",
        }
        return mapping.get(status, "Awaiting update")

    def _match_scores(self, profile: JobSeekerProfile, jobs: list) -> dict:
        scores = {}
        matcher = JobMatchingService()
        for job in jobs:
            if job:
                scores[job.pk] = matcher.score_job(profile, job).score
        return scores

    def _match_score(self, profile: JobSeekerProfile, job) -> int | None:
        if not job:
            return None
        return JobMatchingService().score_job(profile, job).score

    @staticmethod
    def _analytics_cards(
        by_status: dict, active: int
    ) -> list[ApplicationAnalyticsCard]:
        return [
            ApplicationAnalyticsCard(
                "total",
                "Total Applications",
                sum(by_status.values()),
                "bi-briefcase-fill",
                "primary",
            ),
            ApplicationAnalyticsCard(
                "active", "Active", active, "bi-lightning-charge-fill", "info"
            ),
            ApplicationAnalyticsCard(
                "under_review",
                "Under Review",
                by_status.get(JobApplicationStatus.UNDER_REVIEW, 0)
                + by_status.get(JobApplicationStatus.APPLIED, 0),
                "bi-eye-fill",
                "review",
            ),
            ApplicationAnalyticsCard(
                "shortlisted",
                "Shortlisted",
                by_status.get(JobApplicationStatus.SHORTLISTED, 0),
                "bi-star-fill",
                "success",
            ),
            ApplicationAnalyticsCard(
                "interview",
                "Interview Scheduled",
                by_status.get(JobApplicationStatus.INTERVIEW_SCHEDULED, 0),
                "bi-calendar-event-fill",
                "interview",
            ),
            ApplicationAnalyticsCard(
                "offers",
                "Offers Received",
                by_status.get(JobApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(JobApplicationStatus.OFFER_ACCEPTED, 0),
                "bi-envelope-open-heart-fill",
                "offer",
            ),
            ApplicationAnalyticsCard(
                "rejected",
                "Rejected",
                by_status.get(JobApplicationStatus.REJECTED, 0),
                "bi-x-circle-fill",
                "danger",
            ),
            ApplicationAnalyticsCard(
                "hired",
                "Hired",
                by_status.get(JobApplicationStatus.HIRED, 0),
                "bi-trophy-fill",
                "hired",
            ),
            ApplicationAnalyticsCard(
                "withdrawn",
                "Withdrawn",
                by_status.get(JobApplicationStatus.WITHDRAWN, 0),
                "bi-arrow-return-left",
                "muted",
            ),
        ]
