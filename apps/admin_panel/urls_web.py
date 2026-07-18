"""Clean URL routes for Super Admin portal pages."""

from django.urls import path

from apps.admin_panel.views.web import (
    SuperAdminAnalyticsView,
    SuperAdminApplicationListView,

    SuperAdminBillingView,
    SuperAdminDashboardView,
    SuperAdminInvoiceView,
    SuperAdminInvoiceDownloadView,
    SuperAdminInvoiceConfigurationView,
    SuperAdminInvoiceConfigurationPreviewAPIView,
    SuperAdminJobDetailView,
    SuperAdminJobListView,
    SuperAdminNotificationsView,
    SuperAdminOrganizationListView,
    SuperAdminReportsView,
    SuperAdminSettingsView,
    SuperAdminSupportView,
    SuperAdminUserDetailView,
    SuperAdminUserListView,
    SuperAdminUserActionAPIView,
    SuperAdminJobActionAPIView,
    SuperAdminOrganizationActionAPIView,
    SuperAdminGuaranteeClaimsView,
    SuperAdminGuaranteeClaimActionView,
)
from apps.admin_panel.views.claim_api import SuperAdminClaimCandidateSummaryAPIView
from apps.admin_panel.views.application_api import SuperAdminApplicationDetailAPIView
from apps.admin_panel.views.organization_api import SuperAdminOrganizationDetailAPIView

urlpatterns = [
    path("dashboard/", SuperAdminDashboardView.as_view(), name="super_admin_dashboard"),
    path("users/", SuperAdminUserListView.as_view(), name="super_admin_users"),
    path(
        "users/<uuid:user_id>/",
        SuperAdminUserDetailView.as_view(),
        name="super_admin_user_detail",
    ),
    path(
        "users/<uuid:user_id>/action/",
        SuperAdminUserActionAPIView.as_view(),
        name="super_admin_user_action",
    ),
    path(
        "billing/claims/<uuid:claim_id>/candidate-summary/",
        SuperAdminClaimCandidateSummaryAPIView.as_view(),
        name="super_admin_claim_candidate_summary",
    ),
    path("jobs/", SuperAdminJobListView.as_view(), name="super_admin_jobs"),
    path(
        "jobs/<uuid:job_id>/",
        SuperAdminJobDetailView.as_view(),
        name="super_admin_job_detail",
    ),
    path(
        "jobs/<uuid:job_id>/action/",
        SuperAdminJobActionAPIView.as_view(),
        name="super_admin_job_action",
    ),
    path(
        "applications/",
        SuperAdminApplicationListView.as_view(),
        name="super_admin_applications",
    ),
    path(
        "applications/<uuid:application_id>/detail/",
        SuperAdminApplicationDetailAPIView.as_view(),
        name="super_admin_application_detail",
    ),
    path("billing/", SuperAdminBillingView.as_view(), name="super_admin_billing"),
    path("claims/", SuperAdminGuaranteeClaimsView.as_view(), name="super_admin_claims"),
    path("claims/<uuid:claim_id>/action/", SuperAdminGuaranteeClaimActionView.as_view(), name="super_admin_claim_action"),
    path(
        "billing/invoices/<uuid:invoice_id>/view/",
        SuperAdminInvoiceView.as_view(),
        name="super_admin_invoice_view",
    ),
    path(
        "billing/invoices/<uuid:invoice_id>/download/",
        SuperAdminInvoiceDownloadView.as_view(),
        name="super_admin_invoice_download",
    ),
    path(
        "billing/invoice-configuration/",
        SuperAdminInvoiceConfigurationView.as_view(),
        name="super_admin_invoice_configuration",
    ),
    path(
        "billing/invoice-configuration/preview/",
        SuperAdminInvoiceConfigurationPreviewAPIView.as_view(),
        name="super_admin_invoice_configuration_preview",
    ),
    path(
        "organizations/",
        SuperAdminOrganizationListView.as_view(),
        name="super_admin_organizations",
    ),
    path(
        "organizations/<uuid:org_id>/action/",
        SuperAdminOrganizationActionAPIView.as_view(),
        name="super_admin_organization_action",
    ),
    path(
        "organizations/<uuid:org_id>/detail/",
        SuperAdminOrganizationDetailAPIView.as_view(),
        name="super_admin_organization_detail",
    ),
    path("analytics/", SuperAdminAnalyticsView.as_view(), name="super_admin_analytics"),
    path("reports/", SuperAdminReportsView.as_view(), name="super_admin_reports"),
    path("settings/", SuperAdminSettingsView.as_view(), name="super_admin_settings"),

    path(
        "notifications/",
        SuperAdminNotificationsView.as_view(),
        name="super_admin_notifications",
    ),
    path("support/", SuperAdminSupportView.as_view(), name="super_admin_support"),
]
