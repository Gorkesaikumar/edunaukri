from decimal import Decimal, InvalidOperation

from django.db.models import Q, QuerySet
from django.utils.dateparse import parse_date, parse_datetime

from apps.search.constants.enums import MatchMode


class SearchQueryBuilder:
    """Reusable PostgreSQL queryset builder for keyword search, filters, and ordering."""

    def __init__(self, queryset: QuerySet):
        self.queryset = queryset

    def apply_keyword(
        self,
        query: str,
        fields: tuple[str, ...],
        *,
        mode: str = MatchMode.CONTAINS,
        exclude: bool = False,
    ) -> "SearchQueryBuilder":
        if not query or not fields:
            return self
        lookup_map = {
            MatchMode.CONTAINS: "icontains",
            MatchMode.EXACT: "iexact",
            MatchMode.STARTSWITH: "istartswith",
        }
        lookup = lookup_map.get(mode, "icontains")
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__{lookup}": query})
        self.queryset = (
            self.queryset.exclude(condition)
            if exclude
            else self.queryset.filter(condition)
        )
        return self

    def apply_filter(
        self, field: str, value, *, lookup: str = "exact"
    ) -> "SearchQueryBuilder":
        if value is None or value == "":
            return self
        self.queryset = self.queryset.filter(**{f"{field}__{lookup}": value})
        return self

    def apply_boolean(self, field: str, value: bool | None) -> "SearchQueryBuilder":
        if value is None:
            return self
        self.queryset = self.queryset.filter(**{field: value})
        return self

    def apply_date_range(
        self, field: str, start=None, end=None
    ) -> "SearchQueryBuilder":
        if start:
            dt = parse_datetime(start) if isinstance(start, str) else start
            if dt:
                self.queryset = self.queryset.filter(**{f"{field}__gte": dt})
        if end:
            dt = parse_datetime(end) if isinstance(end, str) else end
            if dt:
                self.queryset = self.queryset.filter(**{f"{field}__lte": dt})
        return self

    def apply_numeric_range(
        self, field: str, minimum=None, maximum=None
    ) -> "SearchQueryBuilder":
        min_val = self._to_decimal(minimum)
        max_val = self._to_decimal(maximum)
        if min_val is not None:
            self.queryset = self.queryset.filter(**{f"{field}__gte": min_val})
        if max_val is not None:
            self.queryset = self.queryset.filter(**{f"{field}__lte": max_val})
        return self

    def apply_int_range(
        self, field: str, minimum=None, maximum=None
    ) -> "SearchQueryBuilder":
        min_val = self._to_int(minimum)
        max_val = self._to_int(maximum)
        if min_val is not None:
            self.queryset = self.queryset.filter(**{f"{field}__gte": min_val})
        if max_val is not None:
            self.queryset = self.queryset.filter(**{f"{field}__lte": max_val})
        return self

    def apply_exclude(self, **filters) -> "SearchQueryBuilder":
        cleaned = {k: v for k, v in filters.items() if v not in (None, "")}
        if cleaned:
            self.queryset = self.queryset.exclude(**cleaned)
        return self

    def apply_ordering(self, *fields: str) -> "SearchQueryBuilder":
        if fields:
            self.queryset = self.queryset.order_by(*fields)
        return self

    def optimize(
        self,
        *,
        select_related: tuple[str, ...] | None = None,
        prefetch_related: tuple[str, ...] | None = None,
    ) -> "SearchQueryBuilder":
        if select_related:
            self.queryset = self.queryset.select_related(*select_related)
        if prefetch_related:
            self.queryset = self.queryset.prefetch_related(*prefetch_related)
        return self

    def distinct(self) -> "SearchQueryBuilder":
        self.queryset = self.queryset.distinct()
        return self

    def build(self) -> QuerySet:
        return self.queryset

    @staticmethod
    def _to_decimal(value):
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _to_int(value):
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parse_date(value):
        if not value:
            return None
        if hasattr(value, "year"):
            return value
        return parse_date(value) or parse_datetime(value)
