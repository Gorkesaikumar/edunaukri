from apps.core.services.base import BaseService
from apps.dashboard.selectors.dashboard_selector import DashboardSelector


class DashboardService(BaseService):
    def __init__(self):
        self.selector = DashboardSelector()

    def seeker_dashboard(self, user):
        return self.selector.seeker_summary(user)

    def recruiter_dashboard(self, user):
        return self.selector.recruiter_summary(user)

    def professor_dashboard(self, user):
        return self.selector.professor_summary(user)

    def college_dashboard(self, user):
        return self.selector.college_summary(user)

    def admin_dashboard(self):
        return self.selector.admin_summary()
