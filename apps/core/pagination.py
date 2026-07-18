from django.core.paginator import Paginator
from django.db import connection
from django.utils.functional import cached_property
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response

from apps.core.constants.app_constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from apps.core.utils.pagination import (
    build_page_metadata,
    normalize_page,
    normalize_page_size,
)


class FastPaginator(Paginator):
    @cached_property
    def count(self):
        try:
            # Optimize count for PostgreSQL
            query = getattr(self.object_list, "query", None)
            if query and not query.where:
                table = self.object_list.model._meta.db_table
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT reltuples::int FROM pg_class WHERE relname = %s",
                        [table],
                    )
                    row = cursor.fetchone()
                    if row and row[0] >= 10000:
                        return row[0]
            return super().count
        except Exception:
            return super().count


class StandardResultsSetPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE
    page_query_param = "page"
    django_paginator_class = FastPaginator

    def get_paginated_response(self, data):
        page = normalize_page(self.page.number)
        page_size = normalize_page_size(self.get_page_size(self.request))
        metadata = build_page_metadata(
            count=self.page.paginator.count,
            page=page,
            page_size=page_size,
        )
        return Response(
            {
                "success": True,
                "data": {
                    **metadata,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "results": data,
                },
            }
        )


def paginate_envelope(request, queryset, serializer_class) -> Response:
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(serializer_class(page, many=True).data)


class LargeResultsSetPagination(StandardResultsSetPagination):
    page_size = 50
    max_page_size = 200


class SmallResultsSetPagination(StandardResultsSetPagination):
    page_size = 10
    max_page_size = 50


class StandardCursorPagination(CursorPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE
    ordering = "-created_at"

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "data": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "results": data,
                },
            }
        )
