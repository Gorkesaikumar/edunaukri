"""
Base selector — read-side query abstraction.

Selectors are read-only and optimized for list/detail views.
"""


class BaseSelector:
    """Abstract base for read-side selectors. Phase 1 implementation."""

    model = None
