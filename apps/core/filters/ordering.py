from rest_framework.filters import OrderingFilter

from apps.core.constants.app_constants import DEFAULT_ORDERING_PARAM


class StandardOrderingFilter(OrderingFilter):
    ordering_param = DEFAULT_ORDERING_PARAM
    ordering_fields = "__all__"
