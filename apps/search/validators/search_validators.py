from django.core.exceptions import ValidationError

from apps.core.constants.app_constants import MAX_PAGE_SIZE
from apps.search.constants.field_registry import MAX_QUERY_LENGTH, get_resource_config


class SearchValidator:
    @staticmethod
    def validate_query(query: str | None) -> str:
        if not query:
            return ""
        query = query.strip()
        if len(query) > MAX_QUERY_LENGTH:
            raise ValidationError(
                f"Query must be at most {MAX_QUERY_LENGTH} characters."
            )
        return query

    @staticmethod
    def validate_page_size(page_size) -> int:
        try:
            value = int(page_size)
        except (TypeError, ValueError):
            value = 20
        if value < 1:
            raise ValidationError("Page size must be at least 1.")
        if value > MAX_PAGE_SIZE:
            raise ValidationError(f"Page size must not exceed {MAX_PAGE_SIZE}.")
        return value

    @staticmethod
    def validate_sort(resource: str, sort: str | None) -> str:
        config = get_resource_config(resource)
        default = config["default_sort"]
        if not sort:
            return default
        allowed = config["sort_fields"]
        if sort not in allowed:
            raise ValidationError(f"Invalid sort. Allowed: {', '.join(allowed)}")
        return sort

    @staticmethod
    def validate_filter_key(resource: str, key: str) -> None:
        config = get_resource_config(resource)
        allowed = set(config["filter_fields"]) | {
            config["query_param"],
            "sort",
            "match",
            "page",
            "page_size",
            "pagination_mode",
        }
        if key not in allowed:
            raise ValidationError(f"Filter '{key}' is not allowed for this resource.")
