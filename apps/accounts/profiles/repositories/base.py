from apps.core.repositories.crud import CRUDRepository, ReadRepository


class ReadOnlyProfileRepository(ReadRepository):
    """Read-only base for profile entities."""


class ProfileRepository(CRUDRepository):
    """Write-side base for profile entities with soft-delete support."""
