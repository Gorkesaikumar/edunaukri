"""
Common — models
Django ORM models (Phase 1 implementation). One module per aggregate root.
"""

from apps.common.models.activity import PlatformActivity
from apps.common.models.testimonial import Testimonial

__all__ = ["PlatformActivity", "Testimonial"]
