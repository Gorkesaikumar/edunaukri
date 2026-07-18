from django.urls import path

from apps.academic_recruitment.api.v1.views_admin import (
    AdminCollegeListView,
    AdminVacancyListView,
)
from apps.academic_recruitment.api.v1.views import (
    CollegeFacultyApplicationListView,
    CollegeListCreateView,
    FacultyApplicationDetailView,
    FacultyApplicationListCreateView,
    FacultyApplicationStatusHistoryView,
    FacultyApplicationStatusView,
    FacultyApplicationWithdrawView,
    CollegeVacancyListView,
    ProfessorProfileView,
    VacancyApplicationInboxView,
    VacancyCloseView,
    VacancyDetailView,
    VacancyListCreateView,
    VacancyPublishView,
)
from apps.applications.api.v1.views_faculty import (
    FacultyApplicationNotesView,
    FacultyApplicationTimelineView,
)

urlpatterns = [
    path(
        "profiles/professor/", ProfessorProfileView.as_view(), name="professor-profile"
    ),
    path("colleges/", CollegeListCreateView.as_view(), name="colleges"),
    path("vacancies/", VacancyListCreateView.as_view(), name="vacancies"),
    path("vacancies/mine/", CollegeVacancyListView.as_view(), name="college-vacancies"),
    path(
        "vacancies/<uuid:vacancy_id>/",
        VacancyDetailView.as_view(),
        name="vacancy-detail",
    ),
    path(
        "vacancies/<uuid:vacancy_id>/publish/",
        VacancyPublishView.as_view(),
        name="vacancy-publish",
    ),
    path(
        "vacancies/<uuid:vacancy_id>/close/",
        VacancyCloseView.as_view(),
        name="vacancy-close",
    ),
    path(
        "vacancies/<uuid:vacancy_id>/applications/",
        VacancyApplicationInboxView.as_view(),
        name="vacancy-applications-inbox",
    ),
    path(
        "applications/",
        FacultyApplicationListCreateView.as_view(),
        name="faculty-applications",
    ),
    path(
        "applications/college/",
        CollegeFacultyApplicationListView.as_view(),
        name="college-faculty-applications",
    ),
    path(
        "applications/<uuid:application_id>/",
        FacultyApplicationDetailView.as_view(),
        name="faculty-application-detail",
    ),
    path(
        "applications/<uuid:application_id>/status/",
        FacultyApplicationStatusView.as_view(),
        name="faculty-application-status",
    ),
    path(
        "applications/<uuid:application_id>/withdraw/",
        FacultyApplicationWithdrawView.as_view(),
        name="faculty-application-withdraw",
    ),
    path(
        "applications/<uuid:application_id>/history/",
        FacultyApplicationStatusHistoryView.as_view(),
        name="faculty-application-history",
    ),
    path(
        "applications/<uuid:application_id>/timeline/",
        FacultyApplicationTimelineView.as_view(),
        name="faculty-application-timeline",
    ),
    path(
        "applications/<uuid:application_id>/notes/",
        FacultyApplicationNotesView.as_view(),
        name="faculty-application-notes",
    ),
    path("admin/vacancies/", AdminVacancyListView.as_view(), name="admin-vacancies"),
    path("admin/colleges/", AdminCollegeListView.as_view(), name="admin-colleges"),
]
