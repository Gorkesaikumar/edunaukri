from apps.core.exceptions.domain_exceptions import ResourceNotFoundException
from apps.core.repositories.crud import CRUDRepository
from apps.core.services.base import BaseService
from apps.core.services.transactions import TransactionService


class CRUDService(BaseService):
    """Generic CRUD orchestration — domain services should extend and add rules."""

    repository_class = CRUDRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get(self, pk):
        return self.repository.get_by_id(pk)

    def list(self, **filters):
        if filters:
            return self.repository.filter_by(**filters)
        return self.repository.list_all()

    @TransactionService.service_atomic
    def create(self, **data):
        return self.repository.create(**data)

    @TransactionService.service_atomic
    def update(self, pk, **data):
        instance = self.repository.get_by_id(pk)
        return self.repository.update(instance, **data)

    @TransactionService.service_atomic
    def delete(self, pk):
        instance = self.repository.get_by_id(pk)
        return self.repository.soft_delete(instance)
