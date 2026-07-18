from apps.core.constants.app_constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)


def normalize_page(page) -> int:
    try:
        value = int(page)
    except (TypeError, ValueError):
        return 1
    return max(value, 1)


def normalize_page_size(page_size, *, default: int = DEFAULT_PAGE_SIZE) -> int:
    try:
        value = int(page_size)
    except (TypeError, ValueError):
        value = default
    return max(min(value, MAX_PAGE_SIZE), MIN_PAGE_SIZE)


def build_page_metadata(*, count: int, page: int, page_size: int) -> dict:
    offset = (page - 1) * page_size
    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < count,
        "has_previous": page > 1,
    }
