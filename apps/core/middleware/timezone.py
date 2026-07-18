import zoneinfo

from django.utils import timezone

from apps.core.constants.app_constants import TIMEZONE_HEADER


class TimezoneMiddleware:
    """Activate timezone from X-Timezone header when provided."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = request.headers.get(TIMEZONE_HEADER)
        if tz_name:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tz_name))
            except zoneinfo.ZoneInfoNotFoundError:
                timezone.deactivate()
        else:
            timezone.deactivate()
        response = self.get_response(request)
        timezone.deactivate()
        return response
