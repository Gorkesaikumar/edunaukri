"""Human-readable role labels for Django Admin user listings."""

from __future__ import annotations

from apps.accounts.constants.enums import ITUserRoleType

IT_JOB_SEEKER_LABEL = "IT Job Seeker"
IT_RECRUITER_LABEL = "IT Recruiter"
FACULTY_JOB_SEEKER_LABEL = "Faculty Job Seeker"
FACULTY_RECRUITER_LABEL = "Faculty Recruiter"
UNKNOWN_ROLE_LABEL = "Unknown"

_IT_ROLE_LABELS = {
    ITUserRoleType.JOB_SEEKER: IT_JOB_SEEKER_LABEL,
    ITUserRoleType.RECRUITER: IT_RECRUITER_LABEL,
}


def label_for_it_role(role: str | None) -> str:
    if not role:
        return UNKNOWN_ROLE_LABEL
    return _IT_ROLE_LABELS.get(role, UNKNOWN_ROLE_LABEL)


def resolve_it_user_role(user) -> str | None:
    roles = user.roles.filter(is_deleted=False).order_by("-is_primary", "granted_at")
    primary = roles.filter(is_primary=True).values_list("role", flat=True).first()
    if primary:
        return primary
    return roles.values_list("role", flat=True).first()
