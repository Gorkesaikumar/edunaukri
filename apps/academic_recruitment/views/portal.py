"""Faculty portal views — legacy re-exports."""

from apps.academic_recruitment.views.college_portal import CollegeDashboardView
from apps.academic_recruitment.views.professor_portal import ProfessorDashboardView

__all__ = ["ProfessorDashboardView", "CollegeDashboardView"]
