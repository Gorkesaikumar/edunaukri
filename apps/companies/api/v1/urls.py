"""Companies API v1 endpoints (IT domain)."""

from django.urls import path

from apps.companies.api.v1.views import (
    CompanyActivateView,
    CompanyBrandingView,
    CompanyDashboardView,
    CompanyDeactivateView,
    CompanyDetailView,
    CompanyListCreateView,
    CompanyLocationDetailView,
    CompanyLocationListCreateView,
    CompanyMemberDetailView,
    CompanyMemberListView,
)
from apps.companies.api.v1.views_admin import (
    AdminCompanyDashboardView,
    AdminCompanyDetailView,
    AdminCompanyListView,
    AdminCompanyVerifyView,
)

urlpatterns = [
    path("", CompanyListCreateView.as_view(), name="companies"),
    path(
        "dashboard/summary/", CompanyDashboardView.as_view(), name="company-dashboard"
    ),
    # Admin oversight
    path("admin/", AdminCompanyListView.as_view(), name="admin-companies"),
    path(
        "admin/dashboard/summary/",
        AdminCompanyDashboardView.as_view(),
        name="admin-company-dashboard",
    ),
    path(
        "admin/<uuid:company_id>/",
        AdminCompanyDetailView.as_view(),
        name="admin-company-detail",
    ),
    path(
        "admin/<uuid:company_id>/verify/",
        AdminCompanyVerifyView.as_view(),
        name="admin-company-verify",
    ),
    # Recruiter-scoped company detail & lifecycle
    path("<uuid:company_id>/", CompanyDetailView.as_view(), name="company-detail"),
    path(
        "<uuid:company_id>/activate/",
        CompanyActivateView.as_view(),
        name="company-activate",
    ),
    path(
        "<uuid:company_id>/deactivate/",
        CompanyDeactivateView.as_view(),
        name="company-deactivate",
    ),
    path(
        "<uuid:company_id>/branding/",
        CompanyBrandingView.as_view(),
        name="company-branding",
    ),
    # Locations
    path(
        "<uuid:company_id>/locations/",
        CompanyLocationListCreateView.as_view(),
        name="company-locations",
    ),
    path(
        "<uuid:company_id>/locations/<uuid:location_id>/",
        CompanyLocationDetailView.as_view(),
        name="company-location-detail",
    ),
    # Members (recruiters)
    path(
        "<uuid:company_id>/members/",
        CompanyMemberListView.as_view(),
        name="company-members",
    ),
    path(
        "<uuid:company_id>/members/<uuid:member_id>/",
        CompanyMemberDetailView.as_view(),
        name="company-member-detail",
    ),
]
