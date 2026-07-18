from functools import wraps

from django.db import transaction


def atomic_service_method(func):
    """Wrap a service method in a database transaction."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return func(*args, **kwargs)

    return wrapper


class TransactionService:
    """Transaction orchestration helpers."""

    atomic = staticmethod(transaction.atomic)

    @staticmethod
    def on_commit(func, using=None):
        transaction.on_commit(func, using=using)

    @staticmethod
    def rollback(using=None):
        transaction.set_rollback(True, using=using)

    service_atomic = staticmethod(atomic_service_method)
