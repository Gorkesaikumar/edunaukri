from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import ReportsAPIThrottle

from apps.audit.api.v1.serializers import AuditEventSerializer
from apps.audit.selectors.audit_selector import AuditEventSelector
from apps.core.pagination import StandardResultsSetPagination
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView


class AuditEventListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ReportsAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        queryset = AuditEventSelector().filter_events(
            domain=request.query_params.get("domain"),
            event_type=request.query_params.get("event_type"),
            entity_id=request.query_params.get("entity_id"),
        )
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
