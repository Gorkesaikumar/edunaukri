from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import InvoiceAPIThrottle

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.permissions.roles import IsRecruiter
from apps.core.views.base import EnvelopeAPIView
from apps.invoices.api.v1.serializers import (
    InvoiceCancelSerializer,
    InvoiceGenerateSerializer,
    InvoiceRefundSerializer,
    InvoiceSerializer,
    PaymentCreateSerializer,
    PaymentRecordSerializer,
)
from apps.invoices.permissions.invoice_permissions import CanViewBillingInvoice
from apps.invoices.selectors.invoice_selector import (
    FinancialStatisticsSelector,
    InvoiceSelector,
    OutstandingInvoiceSelector,
    PaidInvoiceSelector,
)
from apps.invoices.services.invoice_lifecycle_service import InvoiceLifecycleService
from apps.invoices.services.invoice_service import InvoiceGenerationService
from apps.invoices.services.payment_tracking_service import PaymentTrackingService
from apps.invoices.services.refund_service import RefundService
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector


class _InvoiceAccessMixin:
    def _scoped_entity_ids(self, request):
        if isinstance(request.user, AdminUser):
            return None
        if isinstance(request.user, ITUser) and IsRecruiter().has_permission(
            request, self
        ):
            recruiter = RecruiterProfileSelector().for_user(request.user)
            if not recruiter:
                return []
            return list(
                CompanyMemberSelector()
                .for_recruiter(recruiter)
                .values_list("company_id", flat=True)
            )
        if isinstance(request.user, CollegeUser):
            return list(
                CollegeMemberSelector()
                .for_user(request.user)
                .values_list("college_id", flat=True)
            )
        return []

    def _invoice_or_error(self, request, invoice_id):
        invoice = InvoiceSelector().get_active(invoice_id)
        if not invoice:
            return None, self.error_response(
                "NOT_FOUND", "Invoice not found.", status=404
            )
        if not CanViewBillingInvoice().has_object_permission(request, self, invoice):
            return None, self.error_response("FORBIDDEN", "Access denied.", status=403)
        return invoice, None


class InvoiceListView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        params = request.query_params
        entity_ids = self._scoped_entity_ids(request)
        if entity_ids == []:
            return self.success_response([])

        if isinstance(request.user, AdminUser):
            invoices = InvoiceSelector().search(
                domain=params.get("domain"),
                status=params.get("status"),
                payment_status=params.get("payment_status"),
                q=params.get("q"),
                ordering=params.get("ordering", "-created_at"),
            )
        elif isinstance(request.user, ITUser):
            invoices = InvoiceSelector().for_company_ids(
                entity_ids,
                domain=params.get("domain"),
                status=params.get("status"),
            )
        else:
            invoices = InvoiceSelector().for_college_ids(
                entity_ids,
                domain=params.get("domain"),
                status=params.get("status"),
            )
        return self.success_response(InvoiceSerializer(invoices, many=True).data)


class InvoiceDetailView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, CanViewBillingInvoice]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request, invoice_id):
        invoice, error = self._invoice_or_error(request, invoice_id)
        if error:
            return error
        return self.success_response(InvoiceSerializer(invoice).data)


class InvoiceGenerateView(EnvelopeAPIView):
    """Internal admin recovery — replays invoice generation for an orphaned placement fee."""

    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        from apps.billing.selectors.fee_selector import PlacementFeeSelector

        serializer = InvoiceGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fee = PlacementFeeSelector().get_active(
            serializer.validated_data["placement_fee_id"]
        )
        if not fee:
            return self.error_response(
                "NOT_FOUND", "Placement fee not found.", status=404
            )
        existing = InvoiceSelector().filter_by(placement_fee_id=fee.pk).first()
        if existing:
            return self.error_response(
                "CONFLICT", "Invoice already exists for this placement fee.", status=409
            )
        invoice = InvoiceGenerationService().generate_from_placement_fee(fee)
        invoice = InvoiceLifecycleService().issue(invoice)
        return self.success_response(
            InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED
        )


class InvoiceCancelView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, invoice_id):
        invoice, error = self._invoice_or_error(request, invoice_id)
        if error:
            return error
        serializer = InvoiceCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = InvoiceLifecycleService().cancel(
            invoice, notes=serializer.validated_data.get("notes", "")
        )
        return self.success_response(InvoiceSerializer(invoice).data)


class InvoicePaymentView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, invoice_id):
        invoice, error = self._invoice_or_error(request, invoice_id)
        if error:
            return error
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = PaymentTrackingService().record_payment(
            invoice, **serializer.validated_data
        )
        invoice.refresh_from_db()
        return self.success_response(
            {
                "payment": PaymentRecordSerializer(payment).data,
                "invoice": InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )


class InvoiceRefundView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, invoice_id):
        invoice, error = self._invoice_or_error(request, invoice_id)
        if error:
            return error
        serializer = InvoiceRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund = RefundService().refund(invoice, **serializer.validated_data)
        invoice.refresh_from_db()
        return self.success_response(
            {
                "refund_id": str(refund.pk),
                "invoice": InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )


from drf_spectacular.utils import extend_schema

class OutstandingInvoiceListView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: InvoiceSerializer(many=True)})
    @extend_schema(responses={200: dict})
    def get(self, request):
        entity_ids = self._scoped_entity_ids(request)
        if entity_ids == []:
            return self.success_response([])
        invoices = OutstandingInvoiceSelector().list(
            domain=request.query_params.get("domain"),
            bill_to_entity_ids=entity_ids
            if not isinstance(request.user, AdminUser)
            else None,
        )
        return self.success_response(InvoiceSerializer(invoices, many=True).data)


class PaidInvoiceListView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: InvoiceSerializer(many=True)})
    @extend_schema(responses={200: dict})
    def get(self, request):
        entity_ids = self._scoped_entity_ids(request)
        if entity_ids == []:
            return self.success_response([])
        invoices = PaidInvoiceSelector().list(
            domain=request.query_params.get("domain"),
            bill_to_entity_ids=entity_ids
            if not isinstance(request.user, AdminUser)
            else None,
        )
        return self.success_response(InvoiceSerializer(invoices, many=True).data)


class FinancialSummaryView(_InvoiceAccessMixin, EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        entity_ids = self._scoped_entity_ids(request)
        if entity_ids == [] and not isinstance(request.user, AdminUser):
            return self.success_response(
                {
                    "total_invoiced": "0",
                    "total_paid": "0",
                    "total_outstanding": "0",
                    "invoice_count": 0,
                    "outstanding_count": 0,
                    "overdue_count": 0,
                    "paid_count": 0,
                    "refunded_count": 0,
                }
            )
        summary = FinancialStatisticsSelector().summary(
            domain=request.query_params.get("domain"),
            bill_to_entity_ids=entity_ids
            if not isinstance(request.user, AdminUser)
            else None,
        )
        return self.success_response(summary)
