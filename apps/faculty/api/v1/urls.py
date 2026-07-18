from django.urls import path

from apps.faculty.api.v1.views import (
    CollegeUserVacancyListView,
    CollegeVacancyListView,
    PublicVacancyDetailView,
    PublicVacancyListView,
    VacancyArchiveView,
    VacancyCloseView,
    VacancyDashboardView,
    VacancyDetailView,
    VacancyDuplicateView,
    VacancyListCreateView,
    VacancyPauseView,
    VacancyPreviewView,
    VacancyPublishView,
    VacancyReopenView,
    VacancyStatisticsView,
    VacancyTemplateListView,
    VacancyUnpublishView,
    VacancyVisibilityView,
)
from apps.faculty.api.v1.views_admin import (
    AdminVacancyDashboardView,
    AdminVacancyDetailView,
    AdminVacancyListView,
    AdminVacancyRejectView,
)

urlpatterns = [
    # Admin oversight (before <uuid> routes)
    path("admin/", AdminVacancyListView.as_view(), name="admin-vacancies"),
    path(
        "admin/dashboard/",
        AdminVacancyDashboardView.as_view(),
        name="admin-vacancy-dashboard",
    ),
    path(
        "admin/<uuid:vacancy_id>/",
        AdminVacancyDetailView.as_view(),
        name="admin-vacancy-detail",
    ),
    path(
        "admin/<uuid:vacancy_id>/reject/",
        AdminVacancyRejectView.as_view(),
        name="admin-vacancy-reject",
    ),
    # Public discovery
    path("public/", PublicVacancyListView.as_view(), name="public-vacancies"),
    path(
        "public/<uuid:vacancy_id>/",
        PublicVacancyDetailView.as_view(),
        name="public-vacancy-detail",
    ),
    # College-user dashboards / scoped lists
    path("mine/", CollegeUserVacancyListView.as_view(), name="college-user-vacancies"),
    path("templates/", VacancyTemplateListView.as_view(), name="vacancy-templates"),
    path("dashboard/", VacancyDashboardView.as_view(), name="vacancy-dashboard"),
    path(
        "college/<uuid:college_id>/",
        CollegeVacancyListView.as_view(),
        name="college-vacancies",
    ),
    # Core CRUD
    path("", VacancyListCreateView.as_view(), name="vacancies"),
    path("<uuid:vacancy_id>/", VacancyDetailView.as_view(), name="vacancy-detail"),
    path(
        "<uuid:vacancy_id>/preview/",
        VacancyPreviewView.as_view(),
        name="vacancy-preview",
    ),
    path(
        "<uuid:vacancy_id>/statistics/",
        VacancyStatisticsView.as_view(),
        name="vacancy-statistics",
    ),
    path(
        "<uuid:vacancy_id>/visibility/",
        VacancyVisibilityView.as_view(),
        name="vacancy-visibility",
    ),
    # Lifecycle actions
    path(
        "<uuid:vacancy_id>/publish/",
        VacancyPublishView.as_view(),
        name="vacancy-publish",
    ),
    path(
        "<uuid:vacancy_id>/unpublish/",
        VacancyUnpublishView.as_view(),
        name="vacancy-unpublish",
    ),
    path("<uuid:vacancy_id>/pause/", VacancyPauseView.as_view(), name="vacancy-pause"),
    path(
        "<uuid:vacancy_id>/reopen/", VacancyReopenView.as_view(), name="vacancy-reopen"
    ),
    path("<uuid:vacancy_id>/close/", VacancyCloseView.as_view(), name="vacancy-close"),
    path(
        "<uuid:vacancy_id>/archive/",
        VacancyArchiveView.as_view(),
        name="vacancy-archive",
    ),
    path(
        "<uuid:vacancy_id>/duplicate/",
        VacancyDuplicateView.as_view(),
        name="vacancy-duplicate",
    ),
]
