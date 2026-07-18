"""Cached resume keyword/skill extraction for dashboard matching."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from django.utils import timezone

from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile


@dataclass
class ResumeAnalysis:
    skills: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    from_cache: bool = True

    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "keywords": self.keywords,
            "projects": self.projects,
            "certifications": self.certifications,
            "from_cache": self.from_cache,
        }


class JobSeekerResumeAnalysisService(BaseService):
    """
    Extract resume signals once and cache on StoredFile.parsed_data.dashboard_cache.
    Recomputes only when resume or profile skill set changes.
    """

    CACHE_KEY = "dashboard_cache"
    CACHE_VERSION = 1

    def get_analysis(
        self, profile: JobSeekerProfile, *, force_refresh: bool = False
    ) -> ResumeAnalysis:
        profile_skill_names = list(
            profile.skills.filter(is_deleted=False)
            .select_related("skill")
            .values_list("skill__name", flat=True)
        )
        fingerprint = self._fingerprint(profile, profile_skill_names)

        if profile.resume_file_id and profile.resume_file and not force_refresh:
            cached = (profile.resume_file.parsed_data or {}).get(self.CACHE_KEY)
            if cached and cached.get("fingerprint") == fingerprint:
                return ResumeAnalysis(
                    skills=cached.get("skills", []),
                    keywords=cached.get("keywords", []),
                    projects=cached.get("projects", []),
                    certifications=cached.get("certifications", []),
                    from_cache=True,
                )

        analysis = self._extract(profile, profile_skill_names)
        if profile.resume_file_id and profile.resume_file:
            self._persist_cache(profile, fingerprint, analysis)
        return analysis

    def invalidate(self, profile: JobSeekerProfile) -> None:
        if not profile.resume_file_id or not profile.resume_file:
            return
        parsed = dict(profile.resume_file.parsed_data or {})
        parsed.pop(self.CACHE_KEY, None)
        profile.resume_file.parsed_data = parsed
        profile.resume_file.parsed_at = timezone.now()
        profile.resume_file.save(
            update_fields=["parsed_data", "parsed_at", "updated_at"]
        )

    def _fingerprint(self, profile: JobSeekerProfile, skill_names: list[str]) -> str:
        parts = [
            str(profile.updated_at),
            str(profile.resume_file_id or ""),
            str(profile.resume_file.updated_at if profile.resume_file_id else ""),
            "|".join(sorted(skill_names)),
            profile.headline or "",
            profile.summary or "",
        ]
        return hashlib.sha256("::".join(parts).encode()).hexdigest()

    def _extract(
        self, profile: JobSeekerProfile, skill_names: list[str]
    ) -> ResumeAnalysis:
        keywords: set[str] = set()
        projects: list[str] = []
        certifications: list[str] = []

        for name in skill_names:
            if name:
                keywords.add(name.lower())

        if profile.headline:
            keywords.update(self._tokenize(profile.headline))
        if profile.summary:
            keywords.update(self._tokenize(profile.summary))

        for exp in profile.experiences.filter(is_deleted=False).only(
            "title", "description", "company_name"
        ):
            keywords.update(self._tokenize(exp.title))
            keywords.update(self._tokenize(exp.description))
            if exp.description and len(exp.description.strip()) > 20:
                projects.append(exp.title or exp.company_name)

        for edu in profile.education.filter(is_deleted=False).only(
            "degree", "field_of_study"
        ):
            keywords.update(self._tokenize(edu.degree))
            keywords.update(self._tokenize(edu.field_of_study))

        resume_data = (
            (profile.resume_file.parsed_data or {}) if profile.resume_file_id else {}
        )
        if isinstance(resume_data.get("skills"), list):
            for item in resume_data["skills"]:
                token = str(item).strip().lower()
                if token:
                    keywords.add(token)
        if isinstance(resume_data.get("keywords"), list):
            keywords.update(
                str(k).strip().lower() for k in resume_data["keywords"] if k
            )
        if isinstance(resume_data.get("projects"), list):
            projects.extend(str(p) for p in resume_data["projects"] if p)
        if isinstance(resume_data.get("certifications"), list):
            certifications.extend(str(c) for c in resume_data["certifications"] if c)

        merged_skills = sorted(
            {s for s in skill_names if s} | {k.title() for k in keywords if len(k) > 2}
        )
        return ResumeAnalysis(
            skills=merged_skills[:50],
            keywords=sorted(keywords)[:120],
            projects=projects[:10],
            certifications=certifications[:10],
            from_cache=False,
        )

    def _persist_cache(
        self, profile: JobSeekerProfile, fingerprint: str, analysis: ResumeAnalysis
    ) -> None:
        stored = profile.resume_file
        parsed = dict(stored.parsed_data or {})
        parsed[self.CACHE_KEY] = {
            "version": self.CACHE_VERSION,
            "fingerprint": fingerprint,
            "analyzed_at": timezone.now().isoformat(),
            "skills": analysis.skills,
            "keywords": analysis.keywords,
            "projects": analysis.projects,
            "certifications": analysis.certifications,
        }
        stored.parsed_data = parsed
        stored.parsed_at = timezone.now()
        stored.save(update_fields=["parsed_data", "parsed_at", "updated_at"])

        from apps.it_recruitment.services.jobseeker_profile_completion_service import (
            JobSeekerProfileCompletionService,
        )

        JobSeekerProfileCompletionService().recalculate(profile)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        if not text:
            return set()
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}", text.lower())
        stop = {
            "and",
            "the",
            "for",
            "with",
            "from",
            "your",
            "our",
            "this",
            "that",
            "have",
            "will",
        }
        return {t for t in tokens if t not in stop and len(t) > 2}
