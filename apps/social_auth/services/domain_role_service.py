"""Domain/role → display name and login URL resolution.

Maps the internal (domain, role) pairs to human-readable portal and role
names for the cross-portal account detection popup, and to the correct
login page URL for redirect.

Domain / Role Matrix
--------------------
+---------------+------------+------------------+----------------------+-------------------------------+
| Domain        | Role       | Portal Display   | Role Display         | Login URL                    |
+---------------+------------+------------------+----------------------+-------------------------------+
| it            | seeker     | IT Recruitment   | Job Seeker           | /it/login/job-seeker/        |
| it            | recruiter  | IT Recruitment   | Recruiter            | /it/login/recruiter/         |
| professor     | seeker     | Faculty          | Professor            | /faculty/login/professor/    |
| college       | institution| Faculty          | Institution          | /faculty/login/institution/  |
+---------------+------------+------------------+----------------------+-------------------------------+
"""

from __future__ import annotations

import logging

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.social_auth.exceptions import CrossDomainLinkedError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Portal display labels for the cross-domain popup
# ---------------------------------------------------------------------------

PORTAL_DISPLAY_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("it", "seeker"): {
        "portal": "IT Recruitment",
        "role_display": "Job Seeker",
        "login_url": "/it/login/job-seeker/",
        "account_display": "IT Job Seeker",
    },
    ("it", "recruiter"): {
        "portal": "IT Recruitment",
        "role_display": "Recruiter",
        "login_url": "/it/login/recruiter/",
        "account_display": "IT Recruiter",
    },
    ("professor", "seeker"): {
        "portal": "Faculty",
        "role_display": "Professor",
        "login_url": "/faculty/login/professor/",
        "account_display": "Faculty Professor",
    },
    ("college", "institution"): {
        "portal": "Faculty",
        "role_display": "Institution",
        "login_url": "/faculty/login/institution/",
        "account_display": "Faculty Institution",
    },
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DomainRoleService:
    """Resolve human-readable portal/role names and login URLs from domain+role pairs.

    Also provides helpers to determine whether two portal references match
    and to resolve the role of a linked user from a ``SocialAccount``.
    """

    @staticmethod
    def portal_info(
        *,
        domain: str,
        role: str,
    ) -> dict[str, str] | None:
        """Return display info for a (domain, role) pair.

        Returns a dict with keys ``portal``, ``role_display``, ``login_url``,
        or ``None`` if the combination is unknown.
        """
        return PORTAL_DISPLAY_MAP.get((domain, role))

    @staticmethod
    def portal_matches(
        *,
        linked_domain: str,
        linked_role: str,
        requested_domain: str,
        requested_role: str,
    ) -> bool:
        """Check whether two portal references point to the same portal.

        Returns ``True`` only when both domain AND role match.
        """
        return linked_domain == requested_domain and linked_role == requested_role

    @staticmethod
    def resolve_user_role(user, domain: str) -> str:
        """Resolve the role for a given user within their domain.

        - ITUser: checks RoleAssignmentService for JOB_SEEKER vs RECRUITER.
        - ProfessorUser: always ``"seeker"``.
        - CollegeUser: always ``"institution"``.

        Defaults to ``"seeker"`` for unknown user types.
        """
        if isinstance(user, ProfessorUser):
            return "seeker"
        if isinstance(user, CollegeUser):
            return "institution"
        if isinstance(user, ITUser):
            roles = RoleAssignmentService()
            if roles.user_has_it_role(user, ITUserRoleType.RECRUITER):
                return "recruiter"
            return "seeker"
        logger.warning(
            "resolve_user_role: unknown user type %s for domain %s",
            type(user).__name__, domain,
        )
        return "seeker"

    @staticmethod
    def resolve_linked_user_info(social_account, linked_user) -> dict[str, str]:
        """Resolve display info for a user linked via a SocialAccount.

        Args:
            social_account: The ``SocialAccount`` instance (used for domain + email).
            linked_user: The resolved local user instance.

        Returns:
            A dict with keys ``email``, ``portal``, ``role_display``,
            ``login_url``, ``account_display`` (or empty strings if
            resolution fails).
        """
        domain = social_account.user_domain
        role = DomainRoleService.resolve_user_role(linked_user, domain)
        info = DomainRoleService.portal_info(domain=domain, role=role) or {}

        return {
            "email": linked_user.email if hasattr(linked_user, "email") else "",
            "portal": info.get("portal", ""),
            "role_display": info.get("role_display", ""),
            "login_url": info.get("login_url", ""),
            "account_display": info.get("account_display", ""),
        }

    @staticmethod
    def validate_portal_match(
        linked_user,
        *,
        linked_domain: str,
        linked_role: str,
        linked_email: str,
        requested_domain: str,
        requested_role: str,
    ) -> None:
        """Check whether the linked user belongs to the requested portal.

        Accepts the linked user's resolved domain, role, and email directly
        so it can be called either from a SocialAccount context or from a
        cross-domain email lookup context (where no SocialAccount exists yet).

        Raises ``CrossDomainLinkedError`` if the linked user's domain/role
        does not match the requested domain/role.
        """
        if DomainRoleService.portal_matches(
            linked_domain=linked_domain,
            linked_role=linked_role,
            requested_domain=requested_domain,
            requested_role=requested_role,
        ):
            return  # Same portal — allow normal login

        info = DomainRoleService.portal_info(domain=linked_domain, role=linked_role) or {}

        raise CrossDomainLinkedError(
            email=linked_email,
            linked_domain=linked_domain,
            linked_role=linked_role,
            linked_portal_display=info.get("portal", ""),
            linked_role_display=info.get("role_display", ""),
            suggested_login_url=info.get("login_url", ""),
            linked_account_display=info.get("account_display", ""),
        )

    @staticmethod
    def validate_portal_match_from_social_account(
        social_account,
        linked_user,
        *,
        requested_domain: str,
        requested_role: str,
    ) -> None:
        """Convenience wrapper that extracts domain/role/email from a SocialAccount.

        Use this when a ``SocialAccount`` record is already available
        (i.e. the ``_find_social_account`` path).
        """
        DomainRoleService.validate_portal_match(
            linked_user,
            linked_domain=social_account.user_domain,
            linked_role=DomainRoleService.resolve_user_role(
                linked_user, social_account.user_domain,
            ),
            linked_email=(
                social_account.email
                or getattr(linked_user, "email", "")
            ),
            requested_domain=requested_domain,
            requested_role=requested_role,
        )
