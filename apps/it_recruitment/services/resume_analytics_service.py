"""Resume analytics and recruiter interaction tracking."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.core.services.base import BaseService
from apps.documents.models import StoredFile
from apps.it_recruitment.models import JobSeekerProfile
from apps.notifications.models import Notification


@dataclass
class ResumeAnalytics:
    views: int = 0
    downloads: int = 0
    recruiter_views: int = 0
    recruiter_downloads: int = 0
    last_viewed_label: str = "—"
    last_downloaded_label: str = "—"
    recruiters_viewed: int = 0
    recruiters_downloaded: int = 0

    def to_dict(self) -> dict:
        return {
            "views": self.views,
            "downloads": self.downloads,
            "recruiter_views": self.recruiter_views,
            "recruiter_downloads": self.recruiter_downloads,
            "last_viewed_label": self.last_viewed_label,
            "last_downloaded_label": self.last_downloaded_label,
            "recruiters_viewed": self.recruiters_viewed,
            "recruiters_downloaded": self.recruiters_downloaded,
        }


class ResumeAnalyticsService(BaseService):
    ANALYTICS_KEY = "analytics"

    def build(self, profile: JobSeekerProfile) -> ResumeAnalytics:
        stored = profile.resume_file if profile.resume_file_id else None
        file_stats = self._file_analytics(stored)
        notif_stats = self._notification_analytics(profile)

        return ResumeAnalytics(
            views=file_stats.get("views", 0) + notif_stats["recruiter_views"],
            downloads=file_stats.get("downloads", 0),
            recruiter_views=notif_stats["recruiter_views"],
            recruiter_downloads=file_stats.get("recruiter_downloads", 0)
            + notif_stats["recruiter_downloads"],
            last_viewed_label=notif_stats["last_viewed_label"]
            or file_stats.get("last_viewed_label", "—"),
            last_downloaded_label=file_stats.get("last_downloaded_label", "—"),
            recruiters_viewed=notif_stats["recruiters_viewed"],
            recruiters_downloaded=file_stats.get("recruiters_downloaded", 0),
        )

    def record_recruiter_download(self, stored: StoredFile) -> None:
        data = dict(stored.parsed_data or {})
        analytics = dict(data.get(self.ANALYTICS_KEY) or {})
        analytics["recruiter_downloads"] = (
            int(analytics.get("recruiter_downloads") or 0) + 1
        )
        analytics["recruiters_downloaded"] = (
            int(analytics.get("recruiters_downloaded") or 0) + 1
        )
        analytics["last_downloaded_at"] = timezone.now().isoformat()
        data[self.ANALYTICS_KEY] = analytics
        stored.parsed_data = data
        stored.save(update_fields=["parsed_data", "updated_at"])

    def _file_analytics(self, stored: StoredFile | None) -> dict:
        if not stored:
            return {}
        raw = (stored.parsed_data or {}).get(self.ANALYTICS_KEY) or {}
        return {
            "views": int(raw.get("views") or 0),
            "downloads": int(raw.get("downloads") or 0),
            "recruiter_downloads": int(raw.get("recruiter_downloads") or 0),
            "recruiters_downloaded": int(raw.get("recruiters_downloaded") or 0),
            "last_viewed_label": self._format_ts(raw.get("last_viewed_at")),
            "last_downloaded_label": self._format_ts(raw.get("last_downloaded_at")),
        }

    def _notification_analytics(self, profile: JobSeekerProfile) -> dict:
        qs = Notification.objects.filter(
            recipient_domain="it",
            recipient_id=profile.user_id,
        )
        viewed = qs.filter(event_type="profile_viewed")
        downloaded = qs.filter(event_type="resume_downloaded")
        last_view = viewed.order_by("-created_at").first()
        return {
            "recruiter_views": viewed.count(),
            "recruiter_downloads": downloaded.count(),
            "recruiters_viewed": viewed.count(),
            "last_viewed_label": (
                timezone.localtime(last_view.created_at).strftime("%b %d, %Y")
                if last_view
                else "—"
            ),
        }

    @staticmethod
    def _format_ts(value) -> str:
        if not value:
            return "—"
        try:
            if isinstance(value, str):
                from datetime import datetime

                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                dt = value
            return timezone.localtime(dt).strftime("%b %d, %Y")
        except (ValueError, TypeError):
            return "—"

    @staticmethod
    def init_on_upload(
        stored: StoredFile, *, previous: StoredFile | None = None
    ) -> None:
        data = dict(stored.parsed_data or {})
        prev = (previous.parsed_data or {}).get("analytics") if previous else {}
        data["analytics"] = {
            "views": int((prev or {}).get("views") or 0),
            "downloads": int((prev or {}).get("downloads") or 0),
            "recruiter_downloads": int((prev or {}).get("recruiter_downloads") or 0),
            "recruiters_downloaded": int(
                (prev or {}).get("recruiters_downloaded") or 0
            ),
            "uploaded_at": timezone.now().isoformat(),
        }
        stored.parsed_data = data
        stored.save(update_fields=["parsed_data", "updated_at"])
