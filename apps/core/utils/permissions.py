from apps.core.utils.pagination import (
    build_page_metadata,
    normalize_page,
    normalize_page_size,
)


def user_owns_resource(*, user, owner_id, owner_type: str | None = None) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if str(getattr(user, "pk", "")) == str(owner_id):
        return True
    if owner_type and getattr(user, "domain", None) == owner_type:
        return str(getattr(user, "pk", "")) == str(owner_id)
    return False
