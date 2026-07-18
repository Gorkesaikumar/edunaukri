"""Job seeker Resume Management Center — dashboard context and insights."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.jobseeker_dashboard_kpi_service import (
    JobSeekerDashboardKPIService,
)
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
    JobSeekerResumeAnalysisService,
)
from apps.it_recruitment.services.resume_analytics_service import ResumeAnalyticsService
from apps.it_recruitment.services.resume_parsing_service import ResumeParsingService


@dataclass
class ResumeSummaryCard:
    key: str
    label: str
    value: str
    icon: str
    tone: str


@dataclass
class ResumeSuggestion:
    message: str
    action_label: str
    action_url: str
    tone: str = "info"


@dataclass
class ResumePortalContext:
    has_resume: bool
    summary: list[ResumeSummaryCard]
    match_score: int
    match_explanation: str
    profile_contribution: int
    suggestions: list[ResumeSuggestion] = field(default_factory=list)
    autofill_suggestions: list[dict] = field(default_factory=list)
    parsed: dict = field(default_factory=dict)
    analysis: dict = field(default_factory=dict)
    analytics: dict = field(default_factory=dict)
    file_name: str = ""
    file_size_label: str = ""
    file_type_label: str = ""
    uploaded_label: str = "—"
    updated_label: str = "—"
    version: int = 0
    storage_status: str = "Not uploaded"
    preview_url: str | None = None
    download_url: str | None = None
    upload_url: str = ""
    delete_url: str = ""
    autofill_url: str = ""
    portal_api_url: str = ""
    is_pdf: bool = False


class JobSeekerResumePortalService(BaseService):
    RESUME_SECTION_WEIGHT = 10

    def build(self, profile: JobSeekerProfile) -> ResumePortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        stored = profile.resume_file if profile.resume_file_id else None
        completion = JobSeekerProfileCompletionService().get_dashboard_state(profile)
        kpis = JobSeekerDashboardKPIService().build(profile)
        analytics = ResumeAnalyticsService().build(profile)
        analysis = JobSeekerResumeAnalysisService().get_analysis(profile)
        parsed = ResumeParsingService().get_extracted(stored) if stored else {}

        has_resume = bool(stored)
        version = (
            int((stored.parsed_data or {}).get("version") or (1 if has_resume else 0))
            if stored
            else 0
        )
        ext = ""
        if stored and stored.original_filename and "." in stored.original_filename:
            ext = stored.original_filename.rsplit(".", 1)[-1].upper()

        preview_url = None
        if stored and ext.lower() == "PDF":
            preview_url = pu("jobseeker_profile_resume_preview")

        match_explanation = self._match_explanation(
            profile, kpis.resume_match_score, analysis
        )

        return ResumePortalContext(
            has_resume=has_resume,
            summary=self._summary_cards(
                profile, stored, completion, kpis, analytics, version
            ),
            match_score=kpis.resume_match_score,
            match_explanation=match_explanation,
            profile_contribution=self.RESUME_SECTION_WEIGHT if has_resume else 0,
            suggestions=self._suggestions(profile, parsed, completion.percentage, pu),
            autofill_suggestions=ResumeParsingService.suggest_profile_autofill(
                parsed, profile
            )
            if parsed
            else [],
            parsed=parsed,
            analysis=analysis.to_dict(),
            analytics=analytics.to_dict(),
            file_name=stored.original_filename if stored else "",
            file_size_label=self._format_size(stored.file_size_bytes if stored else 0),
            file_type_label=ext or "—",
            uploaded_label=self._format_dt(stored.created_at if stored else None),
            updated_label=self._format_dt(stored.updated_at if stored else None),
            version=version or (1 if has_resume else 0),
            storage_status="Active" if has_resume else "Not uploaded",
            preview_url=preview_url,
            download_url=pu("jobseeker_profile_resume_download")
            if has_resume
            else None,
            upload_url=pu("jobseeker_profile_resume_api"),
            delete_url=pu("jobseeker_profile_resume_api"),
            autofill_url=pu("jobseeker_resume_autofill_api"),
            portal_api_url=pu("jobseeker_resume_api"),
            is_pdf=ext.lower() == "pdf",
        )

    def _summary_cards(
        self, profile, stored, completion, kpis, analytics, version
    ) -> list[ResumeSummaryCard]:
        uploaded = "Yes" if stored else "No"
        return [
            ResumeSummaryCard(
                "status",
                "Resume Status",
                uploaded,
                "bi-file-earmark-check",
                "primary" if stored else "muted",
            ),
            ResumeSummaryCard(
                "uploaded",
                "Upload Date",
                self._format_dt(stored.created_at if stored else None),
                "bi-calendar-plus",
                "info",
            ),
            ResumeSummaryCard(
                "updated",
                "Last Updated",
                self._format_dt(stored.updated_at if stored else None),
                "bi-clock-history",
                "review",
            ),
            ResumeSummaryCard(
                "version",
                "Resume Version",
                f"v{version or 0}",
                "bi-layers",
                "interview",
            ),
            ResumeSummaryCard(
                "match",
                "Match Score",
                f"{kpis.resume_match_score}%",
                "bi-bullseye",
                "success",
            ),
            ResumeSummaryCard(
                "completion",
                "Profile Contribution",
                f"+{self.RESUME_SECTION_WEIGHT if stored else 0}%",
                "bi-pie-chart",
                "offer",
            ),
            ResumeSummaryCard(
                "views",
                "Resume Views",
                str(analytics.recruiter_views),
                "bi-eye",
                "info",
            ),
            ResumeSummaryCard(
                "downloads",
                "Recruiter Downloads",
                str(analytics.recruiter_downloads),
                "bi-download",
                "review",
            ),
        ]

    @staticmethod
    def _format_dt(value) -> str:
        if not value:
            return "—"
        return timezone.localtime(value).strftime("%b %d, %Y")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "—"
        if size_bytes < 1024 * 1024:
            return f"{round(size_bytes / 1024, 1)} KB"
        return f"{round(size_bytes / (1024 * 1024), 2)} MB"

    def _match_explanation(self, profile, score: int, analysis) -> str:
        parts: list[str] = []
        snapshot = JobRecommendationCacheService().get_snapshot(profile)
        if snapshot and snapshot.top_match_score:
            parts.append(
                f"Your resume aligns with active listings at up to {snapshot.top_match_score}% match."
            )
        elif score >= 80:
            parts.append(
                "Strong alignment with your skills, experience, and career preferences."
            )
        elif score >= 60:
            parts.append(
                "Good foundation — adding skills and updating experience can improve matches."
            )
        else:
            parts.append(
                "Upload a complete resume and fill profile sections to improve job matches."
            )

        if analysis.skills:
            parts.append(
                f"Detected {len(analysis.skills)} skill signals from your resume."
            )
        if not profile.skills.filter(is_deleted=False).exists():
            parts.append("Add skills to your profile to boost matching accuracy.")
        return " ".join(parts)

    def _suggestions(
        self, profile, parsed: dict, completion_pct: int, pu
    ) -> list[ResumeSuggestion]:
        items: list[ResumeSuggestion] = []
        profile_url = pu("jobseeker_profile")

        if not profile.resume_file_id:
            items.append(
                ResumeSuggestion(
                    "Upload your resume to unlock job matching and recruiter visibility.",
                    "Complete Profile",
                    profile_url,
                    "primary",
                )
            )
            return items

        if not profile.skills.filter(is_deleted=False).exists():
            items.append(
                ResumeSuggestion(
                    "Add more technical skills to improve job match accuracy.",
                    "Add Skills",
                    profile_url + "#jspSkillsSection",
                )
            )
        if not profile.experiences.filter(is_deleted=False).exists():
            items.append(
                ResumeSuggestion(
                    "Include your latest work experience for stronger recruiter impressions.",
                    "Add Experience",
                    profile_url + "#jspExperienceSection",
                )
            )
        if not profile.certifications.filter(
            is_deleted=False
        ).exists() and not parsed.get("certifications"):
            items.append(
                ResumeSuggestion(
                    "Add certifications to stand out for specialized roles.",
                    "Add Certifications",
                    profile_url + "#jspCertificationsSection",
                )
            )
        if not (profile.summary or "").strip():
            items.append(
                ResumeSuggestion(
                    "Write a professional summary highlighting measurable achievements.",
                    "Add Summary",
                    profile_url + "#jspSummarySection",
                )
            )
        if completion_pct < 100:
            items.append(
                ResumeSuggestion(
                    f"Complete missing profile fields to reach 100% ({completion_pct}% now).",
                    "Complete Profile",
                    profile_url,
                    "review",
                )
            )
        if not items:
            items.append(
                ResumeSuggestion(
                    "Your resume profile looks strong. Keep it updated with recent projects and skills.",
                    "View Matches",
                    pu("jobseeker_dashboard"),
                    "success",
                )
            )
        return items[:6]
