from apps.core.selectors.read import ReadSelector
from apps.search.backends.base import PostgreSQLSearchBackend
from apps.search.constants.field_registry import get_resource_config
from apps.search.query.search_query_builder import SearchQueryBuilder


class SearchSelector(ReadSelector):
    """Base reusable search selector driven by resource field registry."""

    resource: str = ""
    backend_class = PostgreSQLSearchBackend

    def search(self, **params):
        config = get_resource_config(self.resource)
        queryset = self.get_base_queryset(**params)
        backend = self.backend_class()
        filters = self._build_filters(config, params)
        order = params.get("order_by") or params.get("sort")
        return backend.apply(
            queryset,
            query=params.get("query", ""),
            search_fields=config["search_fields"],
            match_mode=params.get("match_mode", "contains"),
            filters=filters,
            order_by=order,
            exclude=params.get("exclude"),
        )

    def get_base_queryset(self, **params):
        return self.get_queryset()

    def _build_filters(self, config: dict, params: dict) -> dict:
        filters = {}
        for field, ftype in config["filter_fields"].items():
            value = params.get(field)
            if value is None or value == "":
                continue
            if ftype == "bool":
                filters[field] = {"type": "bool", "value": value}
            elif ftype == "date":
                filters.setdefault(field, {"type": "date_range", "value": {}})
            elif ftype in ("str", "uuid"):
                if field in (
                    "city",
                    "industry",
                    "specialization",
                    "location",
                    "department",
                ):
                    filters[field] = {"type": "icontains", "value": value}
                else:
                    filters[field] = value
        if params.get("created_after"):
            filters["created_at"] = {
                "type": "date_range",
                "value": {
                    "start": params.get("created_after"),
                    "end": params.get("created_before"),
                },
            }
        return filters

    def using_builder(self, queryset, **params) -> SearchQueryBuilder:
        config = get_resource_config(self.resource)
        builder = SearchQueryBuilder(queryset)
        builder.apply_keyword(
            params.get("query", ""),
            config["search_fields"],
            mode=params.get("match_mode", "contains"),
        )
        return builder
