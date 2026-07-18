from apps.applications.models import (
    FacultyApplicationStatusHistory,
    JobApplicationStatusHistory,
)
from apps.core.selectors.read import ReadSelector


class JobApplicationStatusHistorySelector(ReadSelector):
    model = JobApplicationStatusHistory

    def for_application(self, application):
        return self.filter_by(application=application).order_by("-changed_at")


class FacultyApplicationStatusHistorySelector(ReadSelector):
    model = FacultyApplicationStatusHistory

    def for_application(self, application):
        return self.filter_by(application=application).order_by("-changed_at")
