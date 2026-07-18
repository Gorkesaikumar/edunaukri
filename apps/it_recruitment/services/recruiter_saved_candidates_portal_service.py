"""Recruiter saved candidates — shortlisted and active pipeline bookmarks."""

from __future__ import annotations

from dataclasses import dataclass

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.selectors.application_selector import ApplicationSearchSelector
from apps.applications.services.application_statistics_service import (
    ApplicationStatisticsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.recruiter_candidates_portal_service import (
    RecruiterCandidatesPortalService,
)

SAVED_STATUSES = (
    JobApplicationStatus.SHORTLISTED,
    JobApplicationStatus.INTERVIEW_SCHEDULED,
    JobApplicationStatus.INTERVIEW_COMPLETED,
    JobApplicationStatus.OFFER_RELEASED,
    JobApplicationStatus.OFFER_ACCEPTED,
)


@dataclass
class RecruiterSavedCandidatesPortalContext:
    applications: list[dict]
    stats: dict
    api_urls: dict


class RecruiterSavedCandidatesPortalService(BaseService):
    def build(
        self, profile: RecruiterProfile, *, q: str = ""
    ) -> RecruiterSavedCandidatesPortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        portal = RecruiterCandidatesPortalService()

        queryset = (
            ApplicationSearchSelector()
            .search(
                query=q,
                recruiter=profile,
                sort="recent",
            )
            .filter(status__in=SAVED_STATUSES)
        )
        saved_count = queryset.count()
        rows = queryset[:100]

        stats = ApplicationStatisticsService().recruiter_dashboard(profile)

        return RecruiterSavedCandidatesPortalContext(
            applications=[portal._serialize_app(app, pu) for app in rows],
            stats={
                "saved_total": saved_count,
                "shortlisted": stats.get("applications_by_status", {}).get(
                    JobApplicationStatus.SHORTLISTED, 0
                ),
                "interviews": stats.get("applications_by_status", {}).get(
                    JobApplicationStatus.INTERVIEW_SCHEDULED, 0
                ),
                "offers": stats.get("applications_by_status", {}).get(
                    JobApplicationStatus.OFFER_RELEASED, 0
                ),
            },
            api_urls={
                "status_template": pu(
                    "recruiter_application_status_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "notes_template": pu(
                    "recruiter_application_notes_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
                "resume_template": pu(
                    "recruiter_application_resume_api",
                    application_id="00000000-0000-0000-0000-000000000000",
                ),
            },
        )
