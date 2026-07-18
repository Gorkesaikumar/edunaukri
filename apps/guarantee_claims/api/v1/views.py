from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import InvoiceAPIThrottle

from apps.accounts.models.admin_user import AdminUser
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.guarantee_claims.api.v1.serializers import (
    GuaranteeClaimApproveSerializer,
    GuaranteeClaimCreateSerializer,
    GuaranteeClaimRejectSerializer,
    GuaranteeClaimResolveSerializer,
    GuaranteeClaimSerializer,
    GuaranteeClaimStatusSerializer,
)
from apps.guarantee_claims.selectors.claim_selector import GuaranteeClaimSelector
from apps.guarantee_claims.services.claim_service import GuaranteeClaimService
from apps.invoices.permissions.invoice_permissions import CanSubmitGuaranteeClaim
from apps.invoices.selectors.invoice_selector import InvoiceSelector


class GuaranteeClaimListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        claims = GuaranteeClaimSelector().list_by_domain(
            request.query_params.get("domain"),
            status=request.query_params.get("status"),
            invoice_id=request.query_params.get("invoice_id"),
        )
        if not isinstance(request.user, AdminUser):
            accessible_invoice_ids = set(
                InvoiceSelector()
                .search(domain=request.query_params.get("domain"))
                .values_list("pk", flat=True)
            )
            claims = [c for c in claims if c.invoice_id in accessible_invoice_ids]
        return self.success_response(GuaranteeClaimSerializer(claims, many=True).data)

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = GuaranteeClaimCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invoice = InvoiceSelector().get_active(data["invoice_id"])
        if not invoice:
            return self.error_response("NOT_FOUND", "Invoice not found.", status=404)
        if not CanSubmitGuaranteeClaim().has_object_permission(request, self, invoice):
            return self.error_response("FORBIDDEN", "Access denied.", status=403)
        claim = GuaranteeClaimService().submit(**data)
        return self.success_response(
            GuaranteeClaimSerializer(claim).data, status=status.HTTP_201_CREATED
        )


class GuaranteeClaimDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, claim_id):
        claim = GuaranteeClaimSelector().get_active(claim_id)
        if not claim:
            return self.error_response("NOT_FOUND", "Claim not found.", status=404)
        invoice = InvoiceSelector().get_active(claim.invoice_id)
        if invoice and not isinstance(request.user, AdminUser):
            if not CanSubmitGuaranteeClaim().has_object_permission(
                request, self, invoice
            ):
                return self.error_response("FORBIDDEN", "Access denied.", status=403)
        return self.success_response(GuaranteeClaimSerializer(claim).data)


class GuaranteeClaimStatusView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, claim_id):
        claim = GuaranteeClaimSelector().get_active(claim_id)
        if not claim:
            return self.error_response("NOT_FOUND", "Claim not found.", status=404)
        serializer = GuaranteeClaimStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = GuaranteeClaimService().update_status(
            claim,
            serializer.validated_data["status"],
            serializer.validated_data.get("review_notes", ""),
        )
        return self.success_response(GuaranteeClaimSerializer(claim).data)


class GuaranteeClaimApproveView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, claim_id):
        claim = GuaranteeClaimSelector().get_active(claim_id)
        if not claim:
            return self.error_response("NOT_FOUND", "Claim not found.", status=404)
        serializer = GuaranteeClaimApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = GuaranteeClaimService().approve(claim, **serializer.validated_data)
        return self.success_response(GuaranteeClaimSerializer(claim).data)


class GuaranteeClaimRejectView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, claim_id):
        claim = GuaranteeClaimSelector().get_active(claim_id)
        if not claim:
            return self.error_response("NOT_FOUND", "Claim not found.", status=404)
        serializer = GuaranteeClaimRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = GuaranteeClaimService().reject(
            claim, review_notes=serializer.validated_data.get("review_notes", "")
        )
        return self.success_response(GuaranteeClaimSerializer(claim).data)


class GuaranteeClaimResolveView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, claim_id):
        claim = GuaranteeClaimSelector().get_active(claim_id)
        if not claim:
            return self.error_response("NOT_FOUND", "Claim not found.", status=404)
        serializer = GuaranteeClaimResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = GuaranteeClaimService().resolve(
            claim, review_notes=serializer.validated_data.get("review_notes", "")
        )
        return self.success_response(GuaranteeClaimSerializer(claim).data)
