"""Intelligent job-to-seeker matching scores driven by career preferences."""

from __future__ import annotations

import re
from dataclasses import dataclass

from apps.core.services.base import BaseService
from apps.it_recruitment.constants.recommendation_constants import MATCH_WEIGHTS
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
    ResumeAnalysis,
)
from apps.jobs.models import JobPosting


@dataclass
class JobMatchResult:
    job_id: str
    score: int
    breakdown: dict[str, int]


class JobMatchingService(BaseService):
    """Compare seeker profile, career preferences, and resume against job postings."""

    WEIGHTS = MATCH_WEIGHTS

    def score_job(
        self,
        profile: JobSeekerProfile,
        job: JobPosting,
        *,
        analysis: ResumeAnalysis | None = None,
        seeker_skill_ids: set | None = None,
        behavioral_boost: int = 0,
    ) -> JobMatchResult:
        seeker_skill_ids = seeker_skill_ids or set(
            profile.skills.filter(is_deleted=False).values_list("skill_id", flat=True)
        )
        job_skill_ids = {rs.skill_id for rs in job.required_skills.all()}

        skills_raw = self._score_skills(seeker_skill_ids, job_skill_ids)
        keywords_raw = self._score_keywords(analysis, job) if analysis else skills_raw
        skills_combined = min(100, int(skills_raw * 0.7 + keywords_raw * 0.3))

        breakdown = {
            "preferred_role": self._score_preferred_roles(profile, job),
            "skills": skills_combined,
            "experience": self._score_experience(profile, job),
            "location": self._score_location(profile, job),
            "salary": self._score_salary(profile, job),
            "education": self._score_education(profile),
            "work_mode": self._score_work_mode(profile, job),
        }

        weight_total = sum(self.WEIGHTS.values())
        total = sum(breakdown[k] * self.WEIGHTS[k] for k in breakdown) // weight_total
        cert_boost = self._certification_boost(profile, job)
        total = min(99, max(0, total + behavioral_boost + cert_boost))
        if cert_boost:
            breakdown["certifications"] = cert_boost * 10
        return JobMatchResult(job_id=str(job.pk), score=total, breakdown=breakdown)

    def rank_jobs(
        self,
        profile: JobSeekerProfile,
        jobs,
        *,
        analysis: ResumeAnalysis | None = None,
        limit: int = 10,
        behavioral_boosts: dict | None = None,
    ) -> list[tuple[JobPosting, JobMatchResult]]:
        seeker_skill_ids = set(
            profile.skills.filter(is_deleted=False).values_list("skill_id", flat=True)
        )
        boosts = behavioral_boosts or {}
        scored: list[tuple[JobPosting, JobMatchResult]] = []
        for job in jobs:
            boost = boosts.get(job.pk, 0)
            result = self.score_job(
                profile,
                job,
                analysis=analysis,
                seeker_skill_ids=seeker_skill_ids,
                behavioral_boost=boost,
            )
            scored.append((job, result))
        scored.sort(
            key=lambda item: (
                item[1].score,
                item[0].is_featured,
                item[0].published_at or item[0].created_at,
            ),
            reverse=True,
        )
        return scored[:limit]

    @staticmethod
    def _score_skills(seeker_ids: set, job_ids: set) -> int:
        if not job_ids:
            return 75
        if not seeker_ids:
            return 30
        overlap = len(seeker_ids & job_ids)
        ratio = overlap / max(len(job_ids), 1)
        return min(100, int(50 + ratio * 50))

    @staticmethod
    def _score_keywords(analysis: ResumeAnalysis, job: JobPosting) -> int:
        if not analysis.keywords:
            return 40
        corpus = " ".join(
            [
                job.title or "",
                job.description or "",
                job.requirements or "",
                job.category or "",
                job.department or "",
            ]
        ).lower()
        if not corpus.strip():
            return 50
        hits = sum(1 for kw in analysis.keywords[:40] if kw in corpus)
        return min(100, int(40 + hits * 4))

    @staticmethod
    def _score_experience(profile: JobSeekerProfile, job: JobPosting) -> int:
        years = profile.experience_years
        if years is None:
            return profile.experiences.filter(is_deleted=False).exists() and 70 or 35
        min_exp = job.experience_min
        max_exp = job.experience_max
        if min_exp is None and max_exp is None:
            return 80
        if min_exp is not None and years < min_exp:
            gap = min_exp - years
            return max(30, 80 - gap * 15)
        if max_exp is not None and years > max_exp + 5:
            return 65
        return 95

    @staticmethod
    def _score_education(profile: JobSeekerProfile) -> int:
        return 90 if profile.education.filter(is_deleted=False).exists() else 40

    @staticmethod
    def _score_preferred_roles(profile: JobSeekerProfile, job: JobPosting) -> int:
        preferred = (
            profile.preferred_roles if isinstance(profile.preferred_roles, list) else []
        )
        title = (job.title or "").lower()
        category = (job.category or "").lower()
        department = (job.department or "").lower()
        job_corpus = f"{title} {category} {department}"

        if preferred:
            best = 0
            for role in preferred:
                role_lower = str(role).lower().strip()
                if not role_lower:
                    continue
                if role_lower in title or title in role_lower:
                    best = max(best, 100)
                elif role_lower in job_corpus:
                    best = max(best, 88)
                else:
                    role_tokens = set(re.findall(r"[a-z0-9]{3,}", role_lower))
                    job_tokens = set(re.findall(r"[a-z0-9]{3,}", job_corpus))
                    if role_tokens & job_tokens:
                        overlap = len(role_tokens & job_tokens) / max(
                            len(role_tokens), 1
                        )
                        best = max(best, int(55 + overlap * 40))
            if best:
                return min(100, best)

        headline = (profile.headline or "").lower()
        if not headline:
            return 50
        headline_tokens = set(re.findall(r"[a-z]{3,}", headline))
        job_tokens = set(re.findall(r"[a-z]{3,}", job_corpus))
        if not job_tokens:
            return 60
        overlap = len(headline_tokens & job_tokens)
        return min(100, 45 + overlap * 18)

    @staticmethod
    def _score_location(profile: JobSeekerProfile, job: JobPosting) -> int:
        preferred = (
            profile.preferred_location or profile.current_location or ""
        ).lower()
        job_loc = (job.location or job.city or "").lower()
        if job.is_remote or job.work_mode == "remote":
            return 90
        if not preferred or not job_loc:
            return 60
        if preferred in job_loc or job_loc in preferred:
            return 100
        preferred_parts = [p.strip() for p in preferred.split(",") if p.strip()]
        if any(part in job_loc for part in preferred_parts):
            return 85
        return 45

    @staticmethod
    def _score_salary(profile: JobSeekerProfile, job: JobPosting) -> int:
        expected = profile.expected_salary
        if expected is None or job.salary_max is None:
            return 65
        expected_f = float(expected)
        max_f = float(job.salary_max)
        min_f = float(job.salary_min or 0)
        if min_f <= expected_f <= max_f * 1.15:
            return 100
        if expected_f <= max_f * 1.3:
            return 75
        if expected_f > max_f * 1.3:
            return 40
        return 60

    @staticmethod
    def _score_work_mode(profile: JobSeekerProfile, job: JobPosting) -> int:
        preference = profile.work_mode_preference
        job_mode = job.work_mode or ("remote" if job.is_remote else "onsite")
        employment_pref = profile.employment_type_preference
        job_employment = job.employment_type

        mode_score = 70
        if preference:
            if preference == job_mode:
                mode_score = 100
            elif preference == "hybrid" and job_mode in ("remote", "onsite"):
                mode_score = 75
            elif preference == "remote" and job_mode == "hybrid":
                mode_score = 80
            elif preference == "onsite" and job_mode == "hybrid":
                mode_score = 70
            else:
                mode_score = 40

        if employment_pref and job_employment:
            if employment_pref == job_employment:
                return min(100, mode_score + 5)
            return max(30, mode_score - 15)
        return mode_score

    @staticmethod
    def _certification_boost(profile: JobSeekerProfile, job: JobPosting) -> int:
        """Up to +5 match points when active certifications align with the job posting."""
        certs = list(
            profile.certifications.filter(is_deleted=False).values_list(
                "name", "issuing_organization"
            )
        )
        if not certs:
            return 0
        corpus = " ".join(
            [
                job.title or "",
                job.description or "",
                job.requirements or "",
                job.category or "",
                job.department or "",
            ]
        ).lower()
        if not corpus.strip():
            return 0
        hits = 0
        for name, org in certs:
            name_lower = (name or "").lower().strip()
            org_lower = (org or "").lower().strip()
            if name_lower and len(name_lower) >= 4 and name_lower in corpus:
                hits += 1
            elif org_lower and len(org_lower) >= 4 and org_lower in corpus:
                hits += 1
        return min(5, hits * 2)
