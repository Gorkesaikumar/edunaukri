from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import InvoiceAPIThrottle

from apps.billing.api.v1.serializers import (
    FeeScheduleCreateSerializer,
    FeeScheduleSerializer,
    PlacementFeeSerializer,
)
from apps.billing.selectors.fee_selector import (
    FeeScheduleSelector,
    PlacementFeeSelector,
)
from apps.billing.services.placement_fee_service import FeeScheduleService
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView


class FeeScheduleListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        schedules = FeeScheduleSelector().list_by_domain(
            request.query_params.get("domain")
        )
        return self.success_response(FeeScheduleSerializer(schedules, many=True).data)

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = FeeScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = FeeScheduleService().create_schedule(
            data=serializer.validated_data,
            created_by_id=request.user.pk,
        )
        return self.success_response(
            FeeScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED
        )


class PlacementFeeListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [InvoiceAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        fees = PlacementFeeSelector().list_by_domain(request.query_params.get("domain"))
        return self.success_response(PlacementFeeSerializer(fees, many=True).data)
