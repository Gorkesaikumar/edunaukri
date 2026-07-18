"""Web URL routes for Invoices. Phase 1 implementation."""

from django.urls import path
from apps.invoices.views.recruiter import (
    RecruiterInvoicesView,
    RecruiterInvoiceView,
    RecruiterInvoiceDownloadView,
)

urlpatterns = [
    path(
        "recruiter/dashboard/invoices/",
        RecruiterInvoicesView.as_view(),
        name="recruiter_invoices",
    ),
    path(
        "recruiter/dashboard/invoices/<uuid:invoice_id>/view/",
        RecruiterInvoiceView.as_view(),
        name="recruiter_invoice_view",
    ),
    path(
        "recruiter/dashboard/invoices/<uuid:invoice_id>/download/",
        RecruiterInvoiceDownloadView.as_view(),
        name="recruiter_invoice_download",
    ),
]
