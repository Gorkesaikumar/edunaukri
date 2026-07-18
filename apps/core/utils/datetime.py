from django.utils import timezone


def aware_now():
    """Return timezone-aware current datetime."""
    return timezone.now()
