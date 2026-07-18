"""Profile fingerprinting for recommendation cache invalidation."""

from __future__ import annotations

import hashlib
import json

from apps.it_recruitment.models import JobSeekerProfile


def compute_profile_fingerprint(profile: JobSeekerProfile) -> str:
    """Hash career preferences and profile signals that affect matching."""
    skill_ids = list(
        profile.skills.filter(is_deleted=False)
        .order_by("skill_id")
        .values_list("skill_id", flat=True)
    )
    payload = {
        "roles": profile.preferred_roles or [],
        "location": profile.preferred_location or "",
        "salary": str(profile.expected_salary)
        if profile.expected_salary is not None
        else "",
        "employment": profile.employment_type_preference or "",
        "work_mode": profile.work_mode_preference or "",
        "notice": profile.notice_period_days,
        "skills": [str(sid) for sid in skill_ids],
        "resume": str(profile.resume_file_id or ""),
        "exp_years": profile.experience_years,
        "headline": profile.headline or "",
        "exp_count": profile.experiences.filter(is_deleted=False).count(),
        "edu_count": profile.education.filter(is_deleted=False).count(),
        "cert_count": profile.certifications.filter(is_deleted=False).count(),
        "cert_names": sorted(
            profile.certifications.filter(is_deleted=False).values_list(
                "name", flat=True
            )
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
