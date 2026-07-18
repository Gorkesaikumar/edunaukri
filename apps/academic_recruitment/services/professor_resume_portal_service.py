"""Professor CV / resume management center."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService


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
    parsed: dict | None = None
    analytics: dict | None = None


class ProfessorResumePortalService(BaseService):
    CV_SECTION_WEIGHT = 10

    def build(self, profile: ProfessorProfile) -> ResumePortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.professor(user, name, **kw)
        stored = profile.cv_file if profile.cv_file_id else None
        completion = ProfessorProfileCompletionService().get_dashboard_state(profile)

        has_resume = bool(stored)
        ext = ""
        if stored and stored.original_filename and "." in stored.original_filename:
            ext = stored.original_filename.rsplit(".", 1)[-1].upper()

        preview_url = (
            pu("professor_profile_cv_preview")
            if has_resume and ext.lower() == "pdf"
            else None
        )
        score = completion.percentage
        
        parsed_data = None
        parsed_resume = getattr(profile, "parsed_resume", None)
        if parsed_resume and parsed_resume.status == "success":
            parsed_data = {
                "skills": parsed_resume.extracted_skills,
                "education": parsed_resume.extracted_education,
            }
        elif parsed_resume and parsed_resume.status == "processing":
            parsed_data = {"status": "processing"}
        elif parsed_resume and parsed_resume.status == "failed":
            parsed_data = {"status": "failed"}

        return ResumePortalContext(
            has_resume=has_resume,
            summary=self._summary_cards(
                stored, completion.percentage, version=1 if has_resume else 0
            ),
            match_score=score,
            match_explanation=self._match_explanation(profile, score, has_resume),
            profile_contribution=self.CV_SECTION_WEIGHT if has_resume else 0,
            suggestions=self._suggestions(
                profile, completion.percentage, pu, has_resume
            ),
            file_name=stored.original_filename if stored else "",
            file_size_label=self._format_size(stored.file_size_bytes if stored else 0),
            file_type_label=ext or "—",
            uploaded_label=self._format_dt(stored.created_at if stored else None),
            updated_label=self._format_dt(stored.updated_at if stored else None),
            version=1 if has_resume else 0,
            storage_status="Active" if has_resume else "Not uploaded",
            preview_url=preview_url,
            download_url=pu("professor_profile_cv_download") if has_resume else None,
            upload_url=pu("professor_profile_cv_api"),
            delete_url=pu("professor_profile_cv_api"),
            parsed=parsed_data,
            analytics={
                "recruiter_views": getattr(profile, "cv_views_count", 0),
                "recruiter_downloads": getattr(profile, "cv_downloads_count", 0),
                "last_viewed_label": "—",
                "last_downloaded_label": "—",
            },
        )

    def _summary_cards(
        self, stored, completion_pct: int, version: int
    ) -> list[ResumeSummaryCard]:
        return [
            ResumeSummaryCard(
                "status",
                "CV Status",
                "Yes" if stored else "No",
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
                "version", "CV Version", f"v{version}", "bi-layers", "interview"
            ),
            ResumeSummaryCard(
                "completion",
                "Profile Contribution",
                f"+{self.CV_SECTION_WEIGHT if stored else 0}%",
                "bi-pie-chart",
                "offer",
            ),
            ResumeSummaryCard(
                "match",
                "Profile Strength",
                f"{completion_pct}%",
                "bi-bullseye",
                "success",
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

    @staticmethod
    def _match_explanation(profile, score: int, has_resume: bool) -> str:
        if not has_resume:
            return "Upload your CV to unlock stronger faculty applications and institution visibility."
        parts = ["Your CV supports faculty role applications across institutions."]
        if score >= 80:
            parts.append(
                "Your profile is well prepared for competitive faculty openings."
            )
        elif score >= 60:
            parts.append(
                "Complete remaining profile sections to improve match quality."
            )
        else:
            parts.append(
                "Add qualifications, research interests, and experience details."
            )
        if profile.specialization:
            parts.append(f"Specialization: {profile.specialization}.")
        return " ".join(parts)

    @staticmethod
    def _suggestions(
        profile, completion_pct: int, pu, has_resume: bool
    ) -> list[ResumeSuggestion]:
        items: list[ResumeSuggestion] = []
        profile_url = pu("professor_profile")
        if not has_resume:
            return [
                ResumeSuggestion(
                    "Upload your CV to apply to faculty roles and complete your profile.",
                    "Upload CV",
                    pu("professor_resume"),
                    "primary",
                )
            ]
        if completion_pct < 100:
            items.append(
                ResumeSuggestion(
                    "Complete your profile sections to complement your uploaded CV.",
                    "Complete Profile",
                    profile_url,
                )
            )
        if not profile.research_interests:
            items.append(
                ResumeSuggestion(
                    "Add research interests to stand out for academic roles.",
                    "Add Research",
                    profile_url + "#research",
                )
            )
        return items[:4]
