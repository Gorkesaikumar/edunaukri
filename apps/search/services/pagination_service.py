from rest_framework.response import Response

from apps.core.pagination import StandardCursorPagination, StandardResultsSetPagination
from apps.core.utils.pagination import (
    build_page_metadata,
    normalize_page,
    normalize_page_size,
)
from apps.search.constants.enums import PaginationMode
from apps.search.validators.search_validators import SearchValidator


class PaginationService:
    """Reusable pagination for search endpoints."""

    def paginate_response(
        self,
        request,
        queryset,
        serializer_class,
        *,
        mode: str = PaginationMode.PAGE,
        context=None,
    ) -> Response:
        mode = (request.query_params.get("pagination_mode") or mode).lower()
        if mode == PaginationMode.CURSOR:
            return self._cursor_paginate(
                request, queryset, serializer_class, context=context
            )
        if mode == PaginationMode.OFFSET:
            return self._offset_paginate(
                request, queryset, serializer_class, context=context
            )
        return self._page_paginate(request, queryset, serializer_class, context=context)

    def _page_paginate(
        self, request, queryset, serializer_class, *, context=None
    ) -> Response:
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = serializer_class(page, many=True, context=context or {})
        return paginator.get_paginated_response(serializer.data)

    def _cursor_paginate(
        self, request, queryset, serializer_class, *, context=None
    ) -> Response:
        paginator = StandardCursorPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = serializer_class(page, many=True, context=context or {})
        return paginator.get_paginated_response(serializer.data)

    def _offset_paginate(
        self, request, queryset, serializer_class, *, context=None
    ) -> Response:
        page = normalize_page(request.query_params.get("page", 1))
        page_size = SearchValidator.validate_page_size(
            request.query_params.get("page_size", 20)
        )
        total = queryset.count()
        offset = (page - 1) * page_size
        results = queryset[offset : offset + page_size]
        metadata = build_page_metadata(count=total, page=page, page_size=page_size)
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return Response(
            {
                "success": True,
                "data": {
                    **metadata,
                    "total_pages": total_pages,
                    "results": serializer_class(
                        results, many=True, context=context or {}
                    ).data,
                },
            }
        )
