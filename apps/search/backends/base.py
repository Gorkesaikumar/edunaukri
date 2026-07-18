from abc import ABC, abstractmethod

from django.db.models import QuerySet

from apps.search.query.search_query_builder import SearchQueryBuilder


class SearchBackend(ABC):
    """Abstract search backend — swap PostgreSQL for Elasticsearch without API changes."""

    @abstractmethod
    def apply(
        self,
        queryset: QuerySet,
        *,
        query: str = "",
        search_fields: tuple[str, ...] = (),
        match_mode: str = "contains",
        filters: dict | None = None,
        order_by: str | None = None,
        exclude: dict | None = None,
    ) -> QuerySet: ...


class PostgreSQLSearchBackend(SearchBackend):
    """Default PostgreSQL-backed search using SearchQueryBuilder."""

    def apply(
        self,
        queryset: QuerySet,
        *,
        query: str = "",
        search_fields: tuple[str, ...] = (),
        match_mode: str = "contains",
        filters: dict | None = None,
        order_by: str | None = None,
        exclude: dict | None = None,
    ) -> QuerySet:
        builder = SearchQueryBuilder(queryset)
        builder.apply_keyword(query, search_fields, mode=match_mode)
        for field, spec in (filters or {}).items():
            if spec is None or spec == "":
                continue
            if isinstance(spec, dict):
                ftype = spec.get("type")
                value = spec.get("value")
                if ftype == "bool":
                    builder.apply_boolean(field, value)
                elif ftype == "range":
                    builder.apply_numeric_range(
                        field, value.get("min"), value.get("max")
                    )
                elif ftype == "date_range":
                    builder.apply_date_range(
                        field, value.get("start"), value.get("end")
                    )
                elif ftype == "icontains":
                    builder.apply_filter(field, value, lookup="icontains")
                else:
                    builder.apply_filter(field, value)
            else:
                builder.apply_filter(field, spec)
        if exclude:
            builder.apply_exclude(**exclude)
        if order_by:
            if isinstance(order_by, str) and "," in order_by:
                builder.apply_ordering(*order_by.split(","))
            elif isinstance(order_by, (list, tuple)):
                builder.apply_ordering(*order_by)
            else:
                builder.apply_ordering(order_by)
        return builder.build()


class ElasticsearchSearchBackend(SearchBackend):
    """Placeholder for future Elasticsearch integration."""

    def apply(self, queryset: QuerySet, **kwargs) -> QuerySet:
        return PostgreSQLSearchBackend().apply(queryset, **kwargs)
