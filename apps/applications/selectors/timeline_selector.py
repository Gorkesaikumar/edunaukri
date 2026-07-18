from apps.applications.models import (
    FacultyApplicationTimelineEvent,
    JobApplicationTimelineEvent,
)
from apps.core.selectors.read import ReadSelector


class JobApplicationTimelineSelector(ReadSelector):
    model = JobApplicationTimelineEvent

    def for_application(self, application):
        return self.filter_by(application=application).order_by("-occurred_at")


class FacultyApplicationTimelineSelector(ReadSelector):
    model = FacultyApplicationTimelineEvent

    def for_application(self, application):
        return self.filter_by(application=application).order_by("-occurred_at")
