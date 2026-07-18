"""Public "Live Hiring Activity" feed for the landing page.

Streams the newest platform activity across both recruitment domains and
exposes a "today" counter for the social-proof header. Output is a plain list
of DTO dicts so it can serve both the server-rendered section and the JSON
polling endpoint used for auto-refresh.
"""

from django.utils import timezone

from apps.common.constants.enums import ActivityType
from apps.common.models import PlatformActivity

DEFAULT_LIMIT = 12

# type -> (bootstrap icon, accessible verb label)
_TYPE_META = {
    ActivityType.JOB_POSTED: ("bi-briefcase-fill", "Job posted"),
    ActivityType.FACULTY_POSTED: ("bi-mortarboard-fill", "Vacancy posted"),
    ActivityType.CANDIDATE_APPLIED: ("bi-file-earmark-person-fill", "Application"),
    ActivityType.SHORTLISTED: ("bi-list-check", "Shortlisted"),
    ActivityType.INTERVIEW_SCHEDULED: ("bi-calendar-check-fill", "Interview scheduled"),
    ActivityType.OFFER_RELEASED: ("bi-envelope-paper-fill", "Offer released"),
    ActivityType.CANDIDATE_HIRED: ("bi-person-check-fill", "Hired"),
    ActivityType.RECRUITER_VERIFIED: ("bi-patch-check-fill", "Verified"),
    ActivityType.COMPANY_JOINED: ("bi-building-add", "Company joined"),
    ActivityType.UNIVERSITY_JOINED: ("bi-bank2", "University joined"),
}
_DEFAULT_META = ("bi-activity", "Activity")


class ActivityFeedSelector:
    """Read-side builder for the live hiring activity stream."""

    def recent(self, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
        rows = (
            PlatformActivity.objects.filter(is_active=True)
            .select_related("logo_file")
            .order_by("-created_at")[:limit]
        )
        return [self._map(a) for a in rows]

    def today_count(self) -> int:
        start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        return PlatformActivity.objects.filter(
            is_active=True, created_at__gte=start
        ).count()

    def _map(self, a: PlatformActivity) -> dict:
        icon, verb = _TYPE_META.get(a.activity_type, _DEFAULT_META)
        return {
            "id": str(a.id),
            "ts": int(a.created_at.timestamp()) if a.created_at else 0,
            "org_name": a.org_name,
            "headline": a.headline,
            "domain": a.domain,
            "domain_label": a.get_domain_display(),
            "type": a.activity_type,
            "verb": verb,
            "icon": icon,
            "time_display": self._relative(a.created_at),
            "logo_url": self._file_url(a.logo_file),
            "initial": (a.org_name[:1] or "E").upper(),
        }

    @staticmethod
    def _relative(dt) -> str:
        if not dt:
            return ""
        delta = timezone.now() - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return "Just now"
        mins = secs // 60
        if mins < 60:
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        return f"{days} day{'s' if days != 1 else ''} ago"

    @staticmethod
    def _file_url(stored_file) -> str | None:
        if not stored_file or not getattr(stored_file, "storage_path", ""):
            return None
        from django.conf import settings

        path = str(stored_file.storage_path).replace("\\", "/")
        if path.startswith(("http://", "https://", "/")):
            return path
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return f"{media_url}{path.lstrip('/')}"
