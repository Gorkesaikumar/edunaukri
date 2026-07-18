def get_client_ip(request):
    """Extract client IP, honoring X-Forwarded-For when behind a proxy."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def generate_unique_slug(value, model, field="slug", max_length=255):
    """Generate a unique slug for the given model field."""
    from django.utils.text import slugify

    base_slug = slugify(value)[:max_length]
    slug = base_slug
    counter = 1
    while model.all_objects.filter(**{field: slug}).exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug
