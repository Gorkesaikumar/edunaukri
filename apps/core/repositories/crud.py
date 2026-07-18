from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, QuerySet

from apps.core.exceptions.domain_exceptions import ResourceNotFoundException
from apps.core.repositories.base import BaseRepository


class ReadRepository(BaseRepository):
    """Read-only repository operations."""

    def get_queryset(self, *, include_deleted: bool = False) -> QuerySet:
        manager = self._all_manager() if include_deleted else self._manager()
        return manager.all()

    def get_by_id(self, pk, *, include_deleted: bool = False):
        try:
            manager = self._all_manager() if include_deleted else self._manager()
            return manager.get(pk=pk)
        except ObjectDoesNotExist as exc:
            raise ResourceNotFoundException(
                f"{self.model.__name__} not found."
            ) from exc

    def get_by_field(self, field: str, value, *, include_deleted: bool = False):
        try:
            manager = self._all_manager() if include_deleted else self._manager()
            return manager.get(**{field: value})
        except ObjectDoesNotExist as exc:
            raise ResourceNotFoundException(
                f"{self.model.__name__} not found."
            ) from exc

    def exists(self, **filters) -> bool:
        return self._manager().filter(**filters).exists()

    def count(self, **filters) -> int:
        return self._manager().filter(**filters).count()

    def list_all(self, *, order_by: str | None = "-created_at") -> QuerySet:
        queryset = self.get_queryset()
        if order_by:
            return queryset.order_by(order_by)
        return queryset


class FilteringRepository(ReadRepository):
    """Repository filtering and search helpers."""

    search_fields: tuple[str, ...] = ()

    def filter_by(self, **filters) -> QuerySet:
        return self.get_queryset().filter(**filters)

    def search(self, term: str) -> QuerySet:
        if not term or not self.search_fields:
            return self.get_queryset()
        query = Q()
        for field in self.search_fields:
            query |= Q(**{f"{field}__icontains": term})
        return self.get_queryset().filter(query)


class PaginationRepository(ReadRepository):
    """Repository pagination helpers."""

    def paginate(
        self, queryset: QuerySet, *, page: int = 1, page_size: int = 20
    ) -> dict:
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        total = queryset.count()
        offset = (page - 1) * page_size
        results = list(queryset[offset : offset + page_size])
        return {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": results,
            "has_next": offset + page_size < total,
            "has_previous": page > 1,
        }


class CRUDRepository(FilteringRepository, PaginationRepository):
    """Full CRUD repository with filtering and pagination."""

    def create(self, **data):
        return self.model.objects.create(**data)

    def update(self, instance, **data):
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def soft_delete(self, instance):
        if hasattr(instance, "delete") and hasattr(instance, "is_deleted"):
            instance.delete()
            return instance
        raise AttributeError(f"{self.model.__name__} does not support soft delete.")

    def hard_delete(self, instance):
        if hasattr(instance, "hard_delete"):
            instance.hard_delete()
        else:
            instance.delete()
        return instance

    def restore(self, instance):
        if hasattr(instance, "restore"):
            instance.restore()
            return instance
        raise AttributeError(f"{self.model.__name__} does not support restore.")
