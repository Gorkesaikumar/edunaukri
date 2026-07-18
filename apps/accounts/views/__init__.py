"""Accounts views package."""

from apps.accounts.views.tokens import (
    AdminTokenObtainPairView,
    DomainTokenRefreshView,
    FacultyTokenObtainPairView,
    ITTokenObtainPairView,
)

__all__ = [
    "AdminTokenObtainPairView",
    "ITTokenObtainPairView",
    "FacultyTokenObtainPairView",
    "DomainTokenRefreshView",
]
