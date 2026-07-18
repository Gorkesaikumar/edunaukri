"""Public web views (project-level, non-domain pages)."""

import logging

from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.reports.selectors.activity_feed import ActivityFeedSelector
from apps.reports.selectors.featured_jobs import FeaturedJobsSelector
from apps.reports.selectors.hiring_partners import HiringPartnersSelector
from apps.reports.selectors.homepage_stats import HomepageStatsSelector
from apps.reports.selectors.testimonials import TestimonialsSelector

logger = logging.getLogger(__name__)

# Number of records loaded into the unified carousels on first paint.
FEATURED_JOBS_LIMIT = 12
HIRING_PARTNERS_LIMIT = 12
TESTIMONIALS_LIMIT = 12
ACTIVITY_LIMIT = 12

# Neutral defaults used only if live stats cannot be computed (e.g. during
# early setup before migrations). The landing page must never 500 over stats.
_FALLBACK_STATS = {
    "active_jobs": 0,
    "institutions": 0,
    "hiring_success_pct": 0.0,
    "verified_employers": 0,
}


class HomeView(TemplateView):
    """Public marketing homepage with real-time platform statistics."""

    template_name = "pages/homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = self._get_stats()
        context["featured_jobs"] = self._get_featured_jobs()
        partners, partner_filters = self._get_hiring_partners()
        context["hiring_partners"] = partners
        context["partner_filters"] = partner_filters
        context["testimonials"] = self._get_testimonials()
        activities, activity_count = self._get_activity()
        context["activities"] = activities
        context["activity_today"] = activity_count
        return context

    def _get_stats(self) -> dict:
        try:
            return HomepageStatsSelector().public_stats()
        except Exception:  # noqa: BLE001 - resilience: never break the landing page
            logger.exception(
                "Failed to compute homepage platform stats; using fallback."
            )
            return dict(_FALLBACK_STATS)

    def _get_featured_jobs(self) -> list:
        try:
            return FeaturedJobsSelector().latest_unified(limit=FEATURED_JOBS_LIMIT)
        except Exception:  # noqa: BLE001 - resilience: never break the landing page
            logger.exception("Failed to load featured jobs; rendering empty state.")
            return []

    def _get_hiring_partners(self) -> tuple[list, list]:
        try:
            selector = HiringPartnersSelector()
            partners = selector.active_partners(limit=HIRING_PARTNERS_LIMIT)
            return partners, selector.filter_groups(partners)
        except Exception:  # noqa: BLE001 - resilience: never break the landing page
            logger.exception("Failed to load hiring partners; rendering empty state.")
            return [], []

    def _get_testimonials(self) -> list:
        try:
            return TestimonialsSelector().published(limit=TESTIMONIALS_LIMIT)
        except Exception:  # noqa: BLE001 - resilience: never break the landing page
            logger.exception("Failed to load testimonials; rendering empty state.")
            return []

    def _get_activity(self) -> tuple[list, int]:
        try:
            selector = ActivityFeedSelector()
            return selector.recent(limit=ACTIVITY_LIMIT), selector.today_count()
        except Exception:  # noqa: BLE001 - resilience: never break the landing page
            logger.exception("Failed to load live activity; rendering empty state.")
            return [], 0


class AboutView(TemplateView):
    """Public about marketing page."""

    template_name = "pages/about.html"


class DomainSelectionView(TemplateView):
    """Public sign-in entry — choose IT or Faculty domain before login."""

    template_name = "pages/domain_selection.html"

    DOMAINS = (
        {
            "key": "it",
            "title": "IT Domain",
            "description": "For IT Job Seekers and IT Recruiters.",
            "features": (
                "IT Jobs",
                "Software Companies",
                "Tech Recruitment",
                "Resume Management",
                "Applicant Tracking",
            ),
            "button_label": "Continue to IT Portal",
            "url_name": "it_login",
            "icon": "bi-laptop",
            "tone": "primary",
        },
        {
            "key": "faculty",
            "title": "Faculty Domain",
            "description": "For Faculty Job Seekers and Educational Institutions.",
            "features": (
                "Teaching Jobs",
                "Schools",
                "Colleges",
                "Universities",
                "Faculty Recruitment",
            ),
            "button_label": "Continue to Faculty Portal",
            "url_name": "faculty_login",
            "icon": "bi-mortarboard",
            "tone": "secondary",
        },
    )

    def get_context_data(self, **kwargs):
        from django.urls import reverse

        context = super().get_context_data(**kwargs)
        next_url = (self.request.GET.get("next") or "").strip()
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = ""
        domains = []
        for item in self.DOMAINS:
            entry = dict(item)
            url = reverse(entry["url_name"])
            if next_url:
                url = f"{url}?next={next_url}"
            entry["url"] = url
            domains.append(entry)
        context["domains"] = domains
        context["next_url"] = next_url
        return context


class SignupDomainSelectionView(TemplateView):
    """Public registration entry — choose IT or Faculty domain before signup."""

    template_name = "pages/signup_domain_selection.html"

    DOMAINS = (
        {
            "key": "it",
            "title": "IT Domain",
            "description": "Create an account as an IT Job Seeker or IT Recruiter.",
            "features": (
                "Apply for IT Jobs",
                "Hire IT Professionals",
                "Company Dashboard",
                "Resume Management",
                "Applicant Tracking",
            ),
            "button_label": "Get Started with IT",
            "url_name": "it_signup",
            "icon": "bi-laptop",
            "tone": "primary",
        },
        {
            "key": "faculty",
            "title": "Faculty Domain",
            "description": "Create an account as a Faculty Job Seeker or Educational Institution.",
            "features": (
                "Teaching Jobs",
                "School Recruitment",
                "College Recruitment",
                "Faculty Management",
                "Academic Hiring",
            ),
            "button_label": "Get Started with Faculty",
            "url_name": "faculty_signup",
            "icon": "bi-mortarboard",
            "tone": "secondary",
        },
    )

    def get_context_data(self, **kwargs):
        from django.urls import reverse

        context = super().get_context_data(**kwargs)
        next_url = (self.request.GET.get("next") or "").strip()
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = ""
        domains = []
        for item in self.DOMAINS:
            entry = dict(item)
            url = reverse(entry["url_name"])
            if next_url:
                url = f"{url}?next={next_url}"
            entry["url"] = url
            domains.append(entry)
        context["domains"] = domains
        context["next_url"] = next_url
        return context


def live_activity_feed(request):
    """JSON endpoint powering the auto-refreshing Live Hiring Activity feed."""
    try:
        selector = ActivityFeedSelector()
        return JsonResponse(
            {
                "count_today": selector.today_count(),
                "activities": selector.recent(limit=ACTIVITY_LIMIT),
            }
        )
    except Exception:  # noqa: BLE001 - resilience: never break the endpoint
        logger.exception("Live activity feed endpoint failed.")
        return JsonResponse({"count_today": 0, "activities": []}, status=200)
