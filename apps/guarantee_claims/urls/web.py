"""Web URL routes for Guarantee Claims. Phase 1 implementation."""

from django.urls import path
from apps.guarantee_claims.views.api import RecruiterGuaranteeClaimAPIView

urlpatterns = [
    path(
        "api/guarantee-claims/recruiter/submit/",
        RecruiterGuaranteeClaimAPIView.as_view(),
        name="recruiter_submit_claim",
    ),
]
