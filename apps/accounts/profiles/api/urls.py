from django.urls import path

from apps.accounts.profiles.api.v1.views import (
    AdminProfileDetailView,
    AdminProfileStatisticsView,
    MyProfileView,
    ProfileActivateView,
    ProfileCompletionView,
    ProfileDeactivateView,
    PublicProfileView,
)

urlpatterns = [
    path("profiles/me/", MyProfileView.as_view(), name="profile-me"),
    path(
        "profiles/me/completion/",
        ProfileCompletionView.as_view(),
        name="profile-completion",
    ),
    path(
        "profiles/me/deactivate/",
        ProfileDeactivateView.as_view(),
        name="profile-deactivate",
    ),
    path(
        "profiles/me/activate/", ProfileActivateView.as_view(), name="profile-activate"
    ),
    path(
        "profiles/public/<str:profile_type>/<uuid:profile_id>/",
        PublicProfileView.as_view(),
        name="profile-public",
    ),
    path(
        "profiles/admin/statistics/",
        AdminProfileStatisticsView.as_view(),
        name="profile-admin-statistics",
    ),
    path(
        "profiles/admin/<str:profile_type>/<uuid:profile_id>/",
        AdminProfileDetailView.as_view(),
        name="profile-admin-detail",
    ),
]
