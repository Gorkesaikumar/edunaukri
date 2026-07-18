import django_filters

from apps.core.filters.ordering import StandardOrderingFilter
from apps.core.filters.search import StandardSearchFilter


class BaseFilterSet(django_filters.FilterSet):
    """Base filter with common date-range and soft-delete patterns."""

    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    include_deleted = django_filters.BooleanFilter(method="filter_include_deleted")

    def filter_include_deleted(self, queryset, name, value):
        if value:
            return queryset.model.all_objects.filter(
                pk__in=queryset.values_list("pk", flat=True)
            )
        return queryset


__all__ = ["BaseFilterSet", "StandardSearchFilter", "StandardOrderingFilter"]
