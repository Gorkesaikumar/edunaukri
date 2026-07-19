"""Dashboard redirect service — determines user role and returns the correct dashboard URL.

Role resolution
---------------
+----------------------+---------------------+----------------------------+
| User model           | Role                | Dashboard via              |
+----------------------+---------------------+----------------------------+
| AdminUser            | Administrator       | super_admin_dashboard      |
| ProfessorUser        | Faculty Job Seeker  | professor_dashboard        |
| CollegeUser          | Faculty Recruiter   | college_dashboard          |
| ITUser (JOB_SEEKER)  | Job Seeker          | jobseeker_dashboard        |
| ITUser (RECRUITER)   | Recruiter           | recruiter_dashboard        |
+----------------------+---------------------+----------------------------+

Delegates URL resolution to ``PortalURLService.dashboard_for_user()`` so
that dashboard routes stay in sync automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.authentication.services.portal_url_service import PortalURLService


# ---------------------------------------------------------------------------
# Strongly-typed result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DashboardRedirectResult:
    """Result of a dashboard-redirect resolution."""

    role: str
    """Human-readable role label (e.g. ``"Job Seeker"``, ``"Administrator"``)."""

    role_key: str
    """Machine-readable role key (e.g. ``"job_seeker"``, ``"administrator"``)."""

    dashboard_url: str
    """Absolute path to the user's dashboard (ready to pass to ``redirect()``)."""

    user: object = field(repr=False)
    """The user instance, forwarded for convenience."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DashboardRedirectService:
    """Determine a user's role and return the appropriate dashboard URL.

    Usage::

        result = DashboardRedirectService().resolve(user)
        return redirect(result.dashboard_url)
    """

    def resolve(self, user) -> DashboardRedirectResult:
        """Determine the user's role and resolve their dashboard URL.

        Delegates the actual URL to ``PortalURLService.dashboard_for_user()``
        so that any new dashboard routes added there are picked up automatically.

        Args:
            user: Any domain user instance (``AdminUser``, ``ITUser``,
                ``ProfessorUser``, ``CollegeUser``).

        Returns:
            ``DashboardRedirectResult`` with ``role``, ``role_key``,
            ``dashboard_url``, and the original ``user``.

        Raises:
            ValueError: If the user type is not recognised or (for IT
                users) no role assignment is found.
        """
        from apps.accounts.constants.enums import ITUserRoleType
        from apps.accounts.models.admin_user import AdminUser
        from apps.accounts.models.college_user import CollegeUser
        from apps.accounts.models.it_user import ITUser
        from apps.accounts.models.professor_user import ProfessorUser
        from apps.accounts.services.role_assignment_service import (
            RoleAssignmentService,
        )

        # Delegate URL resolution to the canonical source.
        dashboard_url = PortalURLService.dashboard_for_user(user)

        if isinstance(user, AdminUser):
            return DashboardRedirectResult(
                role="Administrator",
                role_key="administrator",
                dashboard_url=dashboard_url,
                user=user,
            )

        if isinstance(user, ProfessorUser):
            return DashboardRedirectResult(
                role="Faculty Job Seeker",
                role_key="faculty_job_seeker",
                dashboard_url=dashboard_url,
                user=user,
            )

        if isinstance(user, CollegeUser):
            return DashboardRedirectResult(
                role="Faculty Recruiter",
                role_key="faculty_recruiter",
                dashboard_url=dashboard_url,
                user=user,
            )

        if isinstance(user, ITUser):
            roles = RoleAssignmentService()
            if roles.user_has_it_role(user, ITUserRoleType.JOB_SEEKER):
                return DashboardRedirectResult(
                    role="Job Seeker",
                    role_key="job_seeker",
                    dashboard_url=dashboard_url,
                    user=user,
                )
            if roles.user_has_it_role(user, ITUserRoleType.RECRUITER):
                return DashboardRedirectResult(
                    role="Recruiter",
                    role_key="recruiter",
                    dashboard_url=dashboard_url,
                    user=user,
                )
            raise ValueError(
                "IT user has neither a Job Seeker nor a Recruiter role "
                "assignment. Cannot determine dashboard."
            )

        raise ValueError(
            f"Cannot resolve dashboard for unrecognised user type "
            f"'{type(user).__name__}'. Expected AdminUser, ITUser, "
            f"ProfessorUser, or CollegeUser."
        )
