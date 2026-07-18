from django.urls import path

from apps.colleges.api.v1.views import (
    InstitutionActivateView,
    InstitutionBrandingView,
    InstitutionCampusDetailView,
    InstitutionCampusListCreateView,
    InstitutionDashboardView,
    InstitutionDeactivateView,
    InstitutionDepartmentDetailView,
    InstitutionDepartmentListView,
    InstitutionDetailView,
    InstitutionDocumentDetailView,
    InstitutionDocumentListView,
    InstitutionListCreateView,
    InstitutionMemberDetailView,
    InstitutionMemberListView,
)
from apps.colleges.api.v1.views_admin import (
    AdminInstitutionDashboardView,
    AdminInstitutionDetailView,
    AdminInstitutionListView,
    AdminInstitutionVerifyView,
)

urlpatterns = [
    # Admin oversight (declared before <uuid> routes to keep "admin" unambiguous)
    path("admin/", AdminInstitutionListView.as_view(), name="admin-institutions"),
    path(
        "admin/dashboard/",
        AdminInstitutionDashboardView.as_view(),
        name="admin-institution-dashboard",
    ),
    path(
        "admin/<uuid:college_id>/",
        AdminInstitutionDetailView.as_view(),
        name="admin-institution-detail",
    ),
    path(
        "admin/<uuid:college_id>/verify/",
        AdminInstitutionVerifyView.as_view(),
        name="admin-institution-verify",
    ),
    # College-facing institution management
    path("", InstitutionListCreateView.as_view(), name="institutions"),
    path(
        "dashboard/", InstitutionDashboardView.as_view(), name="institution-dashboard"
    ),
    path(
        "<uuid:college_id>/", InstitutionDetailView.as_view(), name="institution-detail"
    ),
    path(
        "<uuid:college_id>/activate/",
        InstitutionActivateView.as_view(),
        name="institution-activate",
    ),
    path(
        "<uuid:college_id>/deactivate/",
        InstitutionDeactivateView.as_view(),
        name="institution-deactivate",
    ),
    path(
        "<uuid:college_id>/branding/",
        InstitutionBrandingView.as_view(),
        name="institution-branding",
    ),
    path(
        "<uuid:college_id>/departments/",
        InstitutionDepartmentListView.as_view(),
        name="institution-departments",
    ),
    path(
        "<uuid:college_id>/departments/<uuid:link_id>/",
        InstitutionDepartmentDetailView.as_view(),
        name="institution-department-detail",
    ),
    path(
        "<uuid:college_id>/campuses/",
        InstitutionCampusListCreateView.as_view(),
        name="institution-campuses",
    ),
    path(
        "<uuid:college_id>/campuses/<uuid:campus_id>/",
        InstitutionCampusDetailView.as_view(),
        name="institution-campus-detail",
    ),
    path(
        "<uuid:college_id>/members/",
        InstitutionMemberListView.as_view(),
        name="institution-members",
    ),
    path(
        "<uuid:college_id>/members/<uuid:member_id>/",
        InstitutionMemberDetailView.as_view(),
        name="institution-member-detail",
    ),
    path(
        "<uuid:college_id>/documents/",
        InstitutionDocumentListView.as_view(),
        name="institution-documents",
    ),
    path(
        "<uuid:college_id>/documents/<uuid:document_id>/",
        InstitutionDocumentDetailView.as_view(),
        name="institution-document-detail",
    ),
]
