"""
Base repository — write-side data access abstraction.

All domain repositories extend this class.
Repositories perform persistence only; no business rules.
"""


class BaseRepository:
    """Abstract base for write-side repositories."""

    model = None

    def _manager(self):
        if self.model is None:
            raise NotImplementedError(f"{self.__class__.__name__}.model must be set.")
        return self.model.objects

    def _all_manager(self):
        if self.model is None:
            raise NotImplementedError(f"{self.__class__.__name__}.model must be set.")
        return getattr(self.model, "all_objects", self.model.objects)
