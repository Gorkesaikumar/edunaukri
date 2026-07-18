"""Public job marketplace URL routes."""

from django.urls import path

from apps.jobs.views.marketplace import (
    MarketplaceApplyJobView,
    MarketplaceBrowseView,
    MarketplaceJobDetailView,
    MarketplaceSaveJobView,
    MarketplaceSearchAPIView,
    MarketplaceSuggestAPIView,
    MarketplaceVacancyDetailView,
)

urlpatterns = [
    path("", MarketplaceBrowseView.as_view(), name="marketplace_browse_jobs"),
    path(
        "api/search/", MarketplaceSearchAPIView.as_view(), name="marketplace_search_api"
    ),
    path(
        "api/suggest/",
        MarketplaceSuggestAPIView.as_view(),
        name="marketplace_suggest_api",
    ),
    path(
        "<uuid:job_id>/",
        MarketplaceJobDetailView.as_view(),
        name="marketplace_job_detail",
    ),
    path(
        "faculty/<uuid:job_id>/",
        MarketplaceVacancyDetailView.as_view(),
        name="marketplace_vacancy_detail",
    ),
    path(
        "<uuid:job_id>/apply/",
        MarketplaceApplyJobView.as_view(),
        name="marketplace_job_apply",
    ),
    path(
        "<uuid:job_id>/save/",
        MarketplaceSaveJobView.as_view(),
        name="marketplace_job_save",
    ),
]
