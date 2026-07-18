"""
Base service — business logic and transaction orchestration.

All domain services extend this class.
Views and serializers must delegate to services.
"""

from apps.core.services.transactions import TransactionService


class BaseService:
    """Abstract base for domain services."""

    atomic = staticmethod(TransactionService.atomic)
