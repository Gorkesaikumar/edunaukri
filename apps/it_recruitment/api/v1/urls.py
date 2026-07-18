from django.urls import path

from apps.applications.api.v1.views_it import JobPostingApplicationInboxView
from apps.it_recruitment.api.v1.views_admin import (
    AdminCompanyListView,
    AdminJobPostingListView,
)
from apps.it_recruitment.api.v1.views import (
    CompanyDetailView,
    CompanyListCreateView,
    JobCloseView,
    JobDetailView,
    JobListCreateView,
    JobPublishView,
    JobSeekerProfileView,
    RecruiterJobListView,
    RecruiterProfileView,
)

urlpatterns = [
    path("profiles/seeker/", JobSeekerProfileView.as_view(), name="seeker-profile"),
    path(
        "profiles/recruiter/", RecruiterProfileView.as_view(), name="recruiter-profile"
    ),
    path("companies/", CompanyListCreateView.as_view(), name="companies"),
    path(
        "companies/<uuid:company_id>/",
        CompanyDetailView.as_view(),
        name="company-detail",
    ),
    path("jobs/", JobListCreateView.as_view(), name="jobs"),
    path("jobs/mine/", RecruiterJobListView.as_view(), name="recruiter-jobs"),
    path("jobs/<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<uuid:job_id>/publish/", JobPublishView.as_view(), name="job-publish"),
    path("jobs/<uuid:job_id>/close/", JobCloseView.as_view(), name="job-close"),
    path(
        "jobs/<uuid:job_id>/applications/",
        JobPostingApplicationInboxView.as_view(),
        name="job-applications-inbox",
    ),
    path("admin/jobs/", AdminJobPostingListView.as_view(), name="admin-jobs"),
    path("admin/companies/", AdminCompanyListView.as_view(), name="admin-companies"),
]
