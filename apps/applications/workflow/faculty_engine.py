"""Centralized workflow engine for faculty application status transitions."""

from apps.applications.constants.faculty_enums import (
    FACULTY_LEGACY_STATUS_MAP,
    FACULTY_TERMINAL_STATUSES,
    FacultyApplicationStatus,
)
from apps.applications.constants.transitions import ALLOWED_FACULTY_TRANSITIONS
from apps.core.exceptions.domain_exceptions import BusinessLogicException


class FacultyApplicationWorkflowEngine:
    """Validates and executes faculty application status transitions."""

    transitions = ALLOWED_FACULTY_TRANSITIONS

    @classmethod
    def normalize_status(cls, status: str | None) -> str | None:
        if status is None:
            return None
        return FACULTY_LEGACY_STATUS_MAP.get(status, status)

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
        return cls.normalize_status(status) in FACULTY_TERMINAL_STATUSES

    @classmethod
    def initial_status(cls) -> str:
        return FacultyApplicationStatus.APPLIED
