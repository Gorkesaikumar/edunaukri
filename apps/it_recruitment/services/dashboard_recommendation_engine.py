"""Personalized hero card insights, messaging, and contextual actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.urls import reverse

from django.urls import reverse
from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_matching_service import JobMatchingService
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
    ProfileCompletionResult,
)
from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
    JobSeekerResumeAnalysisService,
    ResumeAnalysis,
)
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting
from apps.notifications.models import Notification


@dataclass
class HeroInsightStat:
    label: str
    value: str
    icon: str


@dataclass
class HeroAction:
    label: str
    url: str
    variant: str = "primary"


@dataclass
class HeroCardContext:
    message: str
    completion_percent: int
    completion_status: str
    completion_sections: list[dict] = field(default_factory=list)
    insight_stats: list[HeroInsightStat] = field(default_factory=list)
    primary_action: HeroAction | None = None
    secondary_action: HeroAction | None = None
    matching_jobs_count: int = 0
    visibility_boost_percent: int = 40

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "completion_percent": self.completion_percent,
            "completion_status": self.completion_status,
            "completion_sections": self.completion_sections,
            "insight_stats": [
                {"label": s.label, "value": s.value, "icon": s.icon}
                for s in self.insight_stats
            ],
            "primary_action": {
                "label": self.primary_action.label,
                "url": self.primary_action.url,
                "variant": self.primary_action.variant,
            }
            if self.primary_action
            else None,
            "secondary_action": {
                "label": self.secondary_action.label,
                "url": self.secondary_action.url,
                "variant": self.secondary_action.variant,
            }
            if self.secondary_action
            else None,
            "matching_jobs_count": self.matching_jobs_count,
            "visibility_boost_percent": self.visibility_boost_percent,
        }


class DashboardRecommendationEngine(BaseService):
    """Build intelligent hero card content from profile, resume, jobs, and activity."""

    def build(self, profile: JobSeekerProfile) -> HeroCardContext | None:
        completion_state = JobSeekerProfileCompletionService().get_dashboard_state(
            profile
        )
        if not completion_state.show_completion_card:
            return None

        completion = ProfileCompletionResult(
            percentage=completion_state.percentage,
            status_label=completion_state.status_label,
            sections=completion_state.sections,
        )
        analysis = JobSeekerResumeAnalysisService().get_analysis(profile)
        metrics = self._collect_metrics(profile, analysis)
        message = self._build_message(profile, completion, metrics)
        primary, secondary = self._build_actions(profile, completion, metrics)
        stats = self._build_insight_stats(metrics)

        return HeroCardContext(
            message=message,
            completion_percent=completion.percentage,
            completion_status=completion.status_label,
            completion_sections=[
                {
                    "key": s.key,
                    "label": s.label,
                    "completed": s.completed,
                    "weight": s.weight,
                }
                for s in completion.sections
            ],
            insight_stats=stats,
            primary_action=primary,
            secondary_action=secondary,
            matching_jobs_count=metrics["matching_jobs_today"],
            visibility_boost_percent=self._visibility_boost(completion.percentage),
        )

    def _collect_metrics(
        self, profile: JobSeekerProfile, analysis: ResumeAnalysis
    ) -> dict:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        applications = JobApplication.objects.filter(
            job_seeker=profile, is_deleted=False
        )
        applied_job_ids = set(applications.values_list("job_posting_id", flat=True))

        published_jobs = JobPosting.objects.filter(
            status=JobStatus.PUBLISHED, is_deleted=False
        ).exclude(pk__in=applied_job_ids)
        jobs_today = published_jobs.filter(published_at__gte=today_start)
        jobs_week = published_jobs.filter(published_at__gte=week_start)

        matcher = JobMatchingService()
        ranked_today = matcher.rank_jobs(
            profile, jobs_today[:30], analysis=analysis, limit=20
        )
        ranked_all = matcher.rank_jobs(
            profile, published_jobs[:40], analysis=analysis, limit=50
        )
        strong_matches = [item for item in ranked_all if item[1].score >= 70]

        recruiter_views_week = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
            created_at__gte=week_start,
        ).count()

        shortlisted = applications.filter(
            status=JobApplicationStatus.SHORTLISTED
        ).count()
        under_review = applications.filter(
            status__in=[
                JobApplicationStatus.APPLIED,
                JobApplicationStatus.UNDER_REVIEW,
            ]
        ).count()
        interview_pending = applications.filter(
            status=JobApplicationStatus.INTERVIEW_SCHEDULED
        ).count()
        applications_count = applications.count()

        role_label = profile.headline or (
            analysis.skills[0] if analysis.skills else "your skills"
        )

        return {
            "matching_jobs_today": len([j for j, r in ranked_today if r.score >= 65]),
            "matching_jobs_total": len(strong_matches),
            "jobs_posted_week": jobs_week.count(),
            "recruiter_views_week": recruiter_views_week,
            "shortlisted": shortlisted,
            "under_review": under_review,
            "interview_pending": interview_pending,
            "applications_count": applications_count,
            "has_resume": bool(profile.resume_file_id),
            "role_label": role_label,
        }

    def _build_message(
        self,
        profile: JobSeekerProfile,
        completion: ProfileCompletionResult,
        metrics: dict,
    ) -> str:
        if metrics["interview_pending"] > 0:
            count = metrics["interview_pending"]
            return (
                f"You have {count} upcoming interview invitation{'s' if count != 1 else ''} "
                f"waiting for your response."
            )

        if not metrics["has_resume"]:
            return "Upload your resume to unlock AI-powered job recommendations."

        if metrics["matching_jobs_today"] > 0:
            count = metrics["matching_jobs_today"]
            role = metrics["role_label"]
            return (
                f"Great news! {count} new {role} job{'s' if count != 1 else ''} matching your skills "
                f"were posted today."
            )

        if metrics["recruiter_views_week"] > 0:
            count = metrics["recruiter_views_week"]
            return f"Your profile was viewed by {count} recruiter{'s' if count != 1 else ''} this week."

        if metrics["under_review"] > 0:
            count = metrics["under_review"]
            return f"You have {count} active application{'s' if count != 1 else ''} currently under review."

        if metrics["applications_count"] == 0 and metrics["matching_jobs_total"] > 0:
            count = metrics["matching_jobs_total"]
            return f"Start applying today. Over {count} matching opportunit{'ies are' if count != 1 else 'y is'} waiting for you."

        if completion.percentage >= 90:
            return "Excellent! Your profile is in the top 10% of candidates this week."

        if completion.percentage < 70:
            boost = self._visibility_boost(completion.percentage)
            return f"Complete your profile to increase recruiter visibility by approximately {boost}%."

        if metrics["matching_jobs_total"] > 0:
            return (
                f"You have {metrics['matching_jobs_total']} job match{'es' if metrics['matching_jobs_total'] != 1 else ''} "
                f"aligned with your experience and preferences."
            )

        return "Keep your profile updated to receive smarter job recommendations."

    def _build_actions(
        self,
        profile: JobSeekerProfile,
        completion: ProfileCompletionResult,
        metrics: dict,
    ) -> tuple[HeroAction, HeroAction]:
        pu = lambda name, **kw: PortalURLService.jobseeker(profile.user, name, **kw)
        if not metrics["has_resume"]:
            return (
                HeroAction("Upload Resume", pu("jobseeker_resume"), "primary"),
                HeroAction("Complete Profile", pu("jobseeker_profile"), "outline"),
            )
        if metrics["interview_pending"] > 0:
            return (
                HeroAction(
                    "Prepare for Interview", pu("jobseeker_interviews"), "primary"
                ),
                HeroAction(
                    "View Applications", pu("jobseeker_applications"), "outline"
                ),
            )
        if completion.percentage < 70:
            return (
                HeroAction("Complete Profile", pu("jobseeker_profile"), "primary"),
                HeroAction("Upload Resume", pu("jobseeker_resume"), "outline"),
            )
        if metrics["matching_jobs_total"] > 0 and metrics["applications_count"] == 0:
            return (
                HeroAction(
                    "View Matching Jobs", reverse("marketplace_browse_jobs"), "primary"
                ),
                HeroAction("Improve Resume", pu("jobseeker_resume"), "outline"),
            )
        if metrics["under_review"] > 0:
            return (
                HeroAction(
                    "Continue Applications", pu("jobseeker_applications"), "primary"
                ),
                HeroAction(
                    "View Matching Jobs", reverse("marketplace_browse_jobs"), "outline"
                ),
            )
        if metrics["matching_jobs_today"] > 0:
            return (
                HeroAction(
                    "View Matching Jobs", reverse("marketplace_browse_jobs"), "primary"
                ),
                HeroAction("Update Profile", pu("jobseeker_profile"), "outline"),
            )
        return (
            HeroAction("Update Profile", pu("jobseeker_profile"), "primary"),
            HeroAction("Resume Tips", pu("jobseeker_resume"), "outline"),
        )

    def _build_insight_stats(self, metrics: dict) -> list[HeroInsightStat]:
        stats = [
            HeroInsightStat(
                label="New Matches Today",
                value=str(metrics["matching_jobs_today"]),
                icon="bi-stars",
            ),
            HeroInsightStat(
                label="Jobs This Week",
                value=str(metrics["jobs_posted_week"]),
                icon="bi-briefcase",
            ),
            HeroInsightStat(
                label="Recruiter Views",
                value=str(metrics["recruiter_views_week"]),
                icon="bi-eye",
            ),
        ]
        if metrics["shortlisted"] > 0:
            stats.append(
                HeroInsightStat(
                    label="Shortlisted",
                    value=str(metrics["shortlisted"]),
                    icon="bi-check2-circle",
                )
            )
        elif metrics["interview_pending"] > 0:
            stats.append(
                HeroInsightStat(
                    label="Interviews",
                    value=str(metrics["interview_pending"]),
                    icon="bi-calendar-event",
                )
            )
        else:
            stats.append(
                HeroInsightStat(
                    label="Active Applications",
                    value=str(metrics["under_review"]),
                    icon="bi-send",
                )
            )
        return stats[:4]

    @staticmethod
    def _visibility_boost(completion_percent: int) -> int:
        remaining = max(0, 100 - completion_percent)
        return min(45, max(15, int(remaining * 0.45)))
