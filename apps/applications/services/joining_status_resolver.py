"""
Centralized joining status resolver — single source of truth for
displaying the joining state in Offer Details, Tracker, and Timeline.

Reads directly from the application model's authoritative fields:
  - application.status (FacultyApplicationStatus / JobApplicationStatus)
  - application.joined_at / application.placed_at / application.hired_at
  - offer timeline event metadata for joining_date if present

Returns a human-readable joining label and optional date string.
"""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone


class JoiningStatusResolver:
    """
    Resolves the joining display label and date for an application.

    Usage:
        label, date_str = JoiningStatusResolver.resolve_faculty(application)
        label, date_str = JoiningStatusResolver.resolve_it(application, offer_meta)
    """

    # ─── Faculty ────────────────────────────────────────────────────────────

    @staticmethod
    def resolve_faculty(application, offer_meta: dict | None = None) -> tuple[str, str | None]:
        """
        Returns (label, optional_date_str) for a FacultyApplication.

        Priority:
          1. application.status maps directly → JOINING_IN_PROGRESS / JOINED
          2. offer_meta has a joining_date key → "Confirmed — <date>"
          3. application.placed_at / joined_at exists → "Confirmed — <date>"
          4. fallback → "To be confirmed"
        """
        from apps.applications.constants.faculty_enums import FacultyApplicationStatus

        status = application.status
        meta = offer_meta or {}

        # 1. Explicit joining lifecycle statuses take highest priority
        if status == FacultyApplicationStatus.JOINING_IN_PROGRESS:
            return "Joining in Progress", None
        if status == FacultyApplicationStatus.JOINED:
            date = JoiningStatusResolver._format_date(
                getattr(application, "joined_at", None)
                or getattr(application, "placed_at", None)
            )
            return "Joined", date

        # 2. Offer metadata joining_date
        if meta.get("joining_date"):
            return "Confirmed", JoiningStatusResolver._parse_meta_date(meta["joining_date"])

        # 3. Application-level placed_at / joined_at
        placed = getattr(application, "placed_at", None) or getattr(application, "joined_at", None)
        if placed:
            return "Confirmed", JoiningStatusResolver._format_date(placed)

        # 4. Offer accepted but no date set yet
        if status == FacultyApplicationStatus.OFFER_ACCEPTED:
            return "Offer Accepted — awaiting joining date", None

        return "To be confirmed", None

    # ─── IT ─────────────────────────────────────────────────────────────────

    @staticmethod
    def resolve_it(application, offer_meta: dict | None = None) -> tuple[str, str | None]:
        """
        Returns (label, optional_date_str) for a JobApplication.

        Priority:
          1. application.status == HIRED / JOINING_IN_PROGRESS
          2. offer_meta has a joining_date key
          3. application.placed_at / hired_at
          4. fallback → "To be confirmed"
        """
        from apps.applications.constants.enums import JobApplicationStatus

        status = application.status
        meta = offer_meta or {}

        if status == JobApplicationStatus.JOINING_IN_PROGRESS:
            return "Joining in Progress", None
        if status == JobApplicationStatus.HIRED:
            date = JoiningStatusResolver._format_date(
                getattr(application, "hired_at", None)
                or getattr(application, "placed_at", None)
            )
            return "Joined", date

        # Offer metadata joining_date
        if meta.get("joining_date"):
            return "Confirmed", JoiningStatusResolver._parse_meta_date(meta["joining_date"])

        # Application-level date
        placed = getattr(application, "placed_at", None) or getattr(application, "hired_at", None)
        if placed:
            return "Confirmed", JoiningStatusResolver._format_date(placed)

        if status == JobApplicationStatus.OFFER_ACCEPTED:
            return "Offer Accepted — awaiting joining date", None

        return "To be confirmed", None

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _format_date(dt) -> str | None:
        if not dt:
            return None
        try:
            local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
            return local.strftime("%d %b %Y")
        except Exception:
            return str(dt)

    @staticmethod
    def _parse_meta_date(value) -> str | None:
        """Parse joining_date from offer metadata (ISO string or date object)."""
        if not value:
            return None
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return JoiningStatusResolver._format_date(dt)
            except ValueError:
                return str(value)
        return JoiningStatusResolver._format_date(value)

    @staticmethod
    def joining_display(label: str, date_str: str | None) -> str:
        """Combine label + optional date into a single display string."""
        if date_str:
            return f"{label} — {date_str}"
        return label
