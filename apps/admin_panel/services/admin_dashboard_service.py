from apps.admin_panel.selectors.dashboard_selector import DashboardSelector
from apps.core.services.base import BaseService
from apps.reports.services.analytics_service import AnalyticsService


class AdminDashboardService(BaseService):
    def __init__(self):
        self.selector = DashboardSelector()

    def summary(self) -> dict:
        base = self.selector.summary()
        kpis = AnalyticsService().platform_overview()
        return {
            **base,
            "platform_kpis": kpis,
        }

    def kpis(self, **filters) -> dict:
        return self.selector.get_kpis(**filters)

    def action_center(self) -> dict:
        return self.selector.action_center()

    def recent_activities(self, *, limit: int = 20) -> list[dict]:
        return self.selector.recent_activities(limit=limit)

    def system_health(self) -> dict:
        return self.selector.system_health()
