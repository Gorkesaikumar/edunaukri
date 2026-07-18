from apps.core.services.base import BaseService
from apps.reports.selectors.platform_kpis import PlatformKPIsSelector


class AnalyticsService(BaseService):
    def __init__(self):
        self.selector = PlatformKPIsSelector()

    def platform_overview(self):
        return self.selector.platform_overview()

    def it_pipeline(self):
        return self.selector.it_pipeline()

    def faculty_pipeline(self):
        return self.selector.faculty_pipeline()
