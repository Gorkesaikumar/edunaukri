"""Reusable search, filtering, sorting, and pagination infrastructure.

Domain-specific query logic lives in each app's ``*SearchSelector`` classes.
This app orchestrates those selectors through ``SearchService`` and exposes
unified ``/api/v1/search/`` endpoints.

Core components:
- ``SearchQueryBuilder`` — PostgreSQL queryset composition
- ``FilterService`` / ``SortingService`` / ``PaginationService``
- ``PostgreSQLSearchBackend`` (default) with ``ElasticsearchSearchBackend`` stub
- ``SearchSelector`` + registry selectors for shared resources
"""

from apps.search.services.filter_service import FilterService
from apps.search.services.pagination_service import PaginationService
from apps.search.services.search_service import SearchService
from apps.search.services.sorting_service import SortingService

__all__ = [
    "FilterService",
    "SortingService",
    "PaginationService",
    "SearchService",
]
