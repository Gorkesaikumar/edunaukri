from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import NotificationsAPIThrottle

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.core.pagination import StandardResultsSetPagination
from apps.core.views.base import EnvelopeAPIView
from apps.notifications.api.v1.serializers import NotificationSerializer
from apps.notifications.selectors.notification_selector import NotificationSelector


def _recipient_domain(user) -> str:
    if isinstance(user, ITUser):
        return "it"
    if isinstance(user, ProfessorUser):
        return "professor"
    if isinstance(user, CollegeUser):
        return "college"
    if isinstance(user, AdminUser):
        return "admin"
    return "unknown"


class NotificationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [NotificationsAPIThrottle]

    from drf_spectacular.utils import extend_schema
    @extend_schema(responses={200: NotificationSerializer(many=True)})
    @extend_schema(responses={200: dict})
    def get(self, request):
        domain = _recipient_domain(request.user)
        unread_only = request.query_params.get("unread") in ("1", "true", "yes")
        queryset = NotificationSelector().for_recipient(
            domain, request.user.pk, unread_only=unread_only
        )
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class NotificationMarkReadView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [NotificationsAPIThrottle]

    from drf_spectacular.utils import extend_schema
    @extend_schema(request=None, responses={200: NotificationSerializer})
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, notification_id):
        domain = _recipient_domain(request.user)
        notification = NotificationSelector().get_for_recipient(
            notification_id, domain, request.user.pk
        )
        if not notification:
            return self.error_response(
                "NOT_FOUND", "Notification not found.", status=404
            )
        notification.mark_read()
        return self.success_response(NotificationSerializer(notification).data)


class NotificationTrackerMarkReadView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [NotificationsAPIThrottle]

    from drf_spectacular.utils import extend_schema
    from rest_framework import serializers
    from drf_spectacular.utils import inline_serializer
    
    @extend_schema(request=None, responses={200: inline_serializer("MarkedReadResponse", {"marked_read": serializers.IntegerField()})})
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        domain = _recipient_domain(request.user)
        # Mark all unread tracker notifications as read
        from apps.notifications.models.notification import Notification
        
        unread_notifications = Notification.objects.filter(
            recipient_id=request.user.pk,
            recipient_domain=domain,
            event_type="application.status_changed",
            is_read=False
        )
        
        count = unread_notifications.count()
        if count > 0:
            from django.utils import timezone
            unread_notifications.update(is_read=True, read_at=timezone.now())
            
        return self.success_response({"marked_read": count})
