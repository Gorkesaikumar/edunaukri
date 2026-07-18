from apps.admin_panel.selectors.analytics_selector import AnalyticsSelector
from apps.core.services.base import BaseService


class AdminAnalyticsService(BaseService):
    def __init__(self):
        self.selector = AnalyticsSelector()

    def overview(self) -> dict:
        return self.selector.overview()

    def enterprise_analytics_overview(self, **filters) -> dict:
        return self.selector.enterprise_analytics_overview(**filters)

    def bi_dashboard_overview(self, **filters) -> dict:
        return self.selector.bi_dashboard_overview(**filters)

    def monthly_placements(self, *, months: int = 12) -> list[dict]:
        return self.selector.monthly_placements(months=months)

    def application_trends(self) -> dict:
        return self.selector.application_trends()

    def revenue_trends(self, *, months: int = 12) -> list[dict]:
        return self.selector.revenue_trends(months=months)
