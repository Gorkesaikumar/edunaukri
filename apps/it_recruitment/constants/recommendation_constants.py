"""Configurable weights and thresholds for the job recommendation engine."""

from __future__ import annotations

# Weighted scoring factors (must sum to 100).
MATCH_WEIGHTS: dict[str, int] = {
    "preferred_role": 30,
    "skills": 25,
    "experience": 15,
    "location": 10,
    "salary": 10,
    "education": 5,
    "work_mode": 5,
}

MIN_MATCH_SCORE = 55
MAX_CACHED_RECOMMENDATIONS = 50
DASHBOARD_RECOMMENDATION_LIMIT = 4
API_RECOMMENDATION_LIMIT = 20

# Jobs below this score are excluded from recommendations.
EXCLUDED_JOB_STATUSES = frozenset({"closed", "expired", "archived", "rejected"})
