"""Institutions Marketplace URL routes."""

from django.urls import path

from apps.reports.views.institution_marketplace import (
    InstitutionDetailView,
    InstitutionsBrowseView,
    InstitutionsSearchAPIView,
    InstitutionsSuggestAPIView,
)

urlpatterns = [
    path("", InstitutionsBrowseView.as_view(), name="institutions_browse"),
    path(
        "api/search/",
        InstitutionsSearchAPIView.as_view(),
        name="institutions_search_api",
    ),
    path(
        "api/suggest/",
        InstitutionsSuggestAPIView.as_view(),
        name="institutions_suggest_api",
    ),
    path("<slug:slug>/", InstitutionDetailView.as_view(), name="institution_detail"),
]
