from django.db.models import QuerySet

from apps.core.exceptions.domain_exceptions import ResourceNotFoundException
from apps.core.repositories.crud import FilteringRepository, PaginationRepository
from apps.core.selectors.base import BaseSelector


class ReadSelector(BaseSelector, FilteringRepository, PaginationRepository):
    """Read-side selector — use in views instead of direct ORM access."""

    def get(self, pk, *, include_deleted: bool = False):
        return self.get_by_id(pk, include_deleted=include_deleted)

    def list(
        self, *, filters: dict | None = None, order_by: str = "-created_at"
    ) -> QuerySet:
        queryset = (
            self.filter_by(**filters) if filters else self.list_all(order_by=order_by)
        )
        return queryset

    def search_list(self, term: str, *, filters: dict | None = None) -> QuerySet:
        queryset = self.search(term)
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    def paginated_list(
        self, *, page: int = 1, page_size: int = 20, filters: dict | None = None
    ) -> dict:
        queryset = self.list(filters=filters)
        return self.paginate(queryset, page=page, page_size=page_size)

    def get_or_none(self, pk):
        try:
            return self.get(pk)
        except ResourceNotFoundException:
            return None
