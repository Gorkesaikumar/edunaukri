"""Public "Success Stories" feed for the landing page.

Surfaces only testimonials that are approved, active, public and verified,
newest first. Normalises rows into lightweight DTO dicts (with success
badges + a truncated quote flag) so the template stays dumb.
"""

from apps.common.constants.enums import TestimonialVisibility
from apps.common.models import Testimonial

DEFAULT_LIMIT = 12
QUOTE_PREVIEW_CHARS = 160


class TestimonialsSelector:
    """Read-side builder for verified placement success stories."""

    def published(self, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
        rows = (
            Testimonial.objects.filter(
                is_active=True,
                is_verified=True,
                visibility=TestimonialVisibility.PUBLIC,
            )
            .select_related("photo_file")
            .order_by("-published_at", "-created_at")[:limit]
        )
        return [self._map(t) for t in rows]

    def _map(self, t: Testimonial) -> dict:
        quote = t.quote or ""
        is_long = len(quote) > QUOTE_PREVIEW_CHARS
        rating = max(0, min(int(t.rating or 0), 5))
        return {
            "author_name": t.author_name,
            "designation": t.designation,
            "organization_name": t.organization_name,
            "domain": t.domain,
            "domain_label": t.get_domain_display(),
            "rating": rating,
            "rating_range": range(rating),
            "empty_range": range(5 - rating),
            "quote": quote,
            "quote_is_long": is_long,
            "photo_url": self._file_url(t.photo_file),
            "initial": (t.author_name[:1] or "E").upper(),
            "badges": self._badges(t),
            # Data attributes consumed by client-side filter/sort.
            "salary_increase_pct": t.salary_increase_pct or 0,
            "days_to_hire": t.days_to_hire or 0,
        }

    @staticmethod
    def _badges(t: Testimonial) -> list[dict]:
        badges: list[dict] = [
            {"icon": "bi-patch-check-fill", "label": "Placed via EduNaukri"}
        ]
        if t.days_to_hire:
            badges.append(
                {
                    "icon": "bi-lightning-charge-fill",
                    "label": f"Hired in {t.days_to_hire} Days",
                }
            )
        if t.salary_increase_pct:
            badges.append(
                {
                    "icon": "bi-graph-up-arrow",
                    "label": f"Salary up {t.salary_increase_pct}%",
                }
            )
        if t.joined_dream_company:
            badges.append({"icon": "bi-stars", "label": "Joined Dream Company"})
        if t.is_verified:
            badges.append({"icon": "bi-shield-check", "label": "Verified Placement"})
        return badges

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
