"""Centralized workflow engine for job application status transitions."""

from apps.applications.constants.enums import LEGACY_STATUS_MAP, JobApplicationStatus
from apps.applications.constants.transitions import ALLOWED_IT_TRANSITIONS
from apps.core.exceptions.domain_exceptions import BusinessLogicException


class ApplicationWorkflowEngine:
    """Validates and executes IT job application status transitions."""

    transitions = ALLOWED_IT_TRANSITIONS

    @classmethod
    def normalize_status(cls, status: str | None) -> str | None:
        if status is None:
            return None
        return LEGACY_STATUS_MAP.get(status, status)

    @classmethod
    def can_transition(cls, from_status: str | None, to_status: str) -> bool:
        current = cls.normalize_status(from_status)
        target = cls.normalize_status(to_status)
        return target in cls.transitions.get(current, set())

    @classmethod
    def validate_transition(cls, from_status: str | None, to_status: str) -> None:
        current = cls.normalize_status(from_status)
        target = cls.normalize_status(to_status)
        if target not in cls.transitions.get(current, set()):
            raise BusinessLogicException(
                f"Cannot transition from {current or 'new'} to {target}."
            )

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        from apps.applications.constants.enums import TERMINAL_STATUSES

        return cls.normalize_status(status) in TERMINAL_STATUSES

    @classmethod
    def initial_status(cls) -> str:
        return JobApplicationStatus.APPLIED
