from django.urls import path

from apps.invoices.api.v1.views import (
    FinancialSummaryView,
    InvoiceCancelView,
    InvoiceDetailView,
    InvoiceGenerateView,
    InvoiceListView,
    InvoicePaymentView,
    InvoiceRefundView,
    OutstandingInvoiceListView,
    PaidInvoiceListView,
)

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoices"),
    path(
        "outstanding/",
        OutstandingInvoiceListView.as_view(),
        name="invoices-outstanding",
    ),
    path("paid/", PaidInvoiceListView.as_view(), name="invoices-paid"),
    path("summary/", FinancialSummaryView.as_view(), name="invoices-summary"),
    path("generate/", InvoiceGenerateView.as_view(), name="invoice-generate-internal"),
    path("<uuid:invoice_id>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path(
        "<uuid:invoice_id>/cancel/", InvoiceCancelView.as_view(), name="invoice-cancel"
    ),
    path(
        "<uuid:invoice_id>/payments/",
        InvoicePaymentView.as_view(),
        name="invoice-payment",
    ),
    path(
        "<uuid:invoice_id>/refund/", InvoiceRefundView.as_view(), name="invoice-refund"
    ),
]
