from django.urls import path

from apps.guarantee_claims.api.v1.views import (
    GuaranteeClaimApproveView,
    GuaranteeClaimDetailView,
    GuaranteeClaimListCreateView,
    GuaranteeClaimRejectView,
    GuaranteeClaimResolveView,
    GuaranteeClaimStatusView,
)

urlpatterns = [
    path("", GuaranteeClaimListCreateView.as_view(), name="guarantee-claims"),
    path(
        "<uuid:claim_id>/",
        GuaranteeClaimDetailView.as_view(),
        name="guarantee-claim-detail",
    ),
    path(
        "<uuid:claim_id>/status/",
        GuaranteeClaimStatusView.as_view(),
        name="guarantee-claim-status",
    ),
    path(
        "<uuid:claim_id>/approve/",
        GuaranteeClaimApproveView.as_view(),
        name="guarantee-claim-approve",
    ),
    path(
        "<uuid:claim_id>/reject/",
        GuaranteeClaimRejectView.as_view(),
        name="guarantee-claim-reject",
    ),
    path(
        "<uuid:claim_id>/resolve/",
        GuaranteeClaimResolveView.as_view(),
        name="guarantee-claim-resolve",
    ),
]
