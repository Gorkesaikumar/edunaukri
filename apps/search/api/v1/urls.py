from django.urls import path

from apps.search.api.v1.views import (
    AdminGlobalSearchView,
    ApplicationSearchView,
    CollegeSearchView,
    CompanySearchView,
    GuaranteeSearchView,
    InvoiceSearchView,
    JobSearchView,
    JobSeekerSearchView,
    ProfessorSearchView,
    RecruiterSearchView,
    VacancySearchView,
)

urlpatterns = [
    path("jobs/", JobSearchView.as_view(), name="search-jobs"),
    path("vacancies/", VacancySearchView.as_view(), name="search-vacancies"),
    path("faculty/", VacancySearchView.as_view(), name="search-faculty"),
    path("companies/", CompanySearchView.as_view(), name="search-companies"),
    path("colleges/", CollegeSearchView.as_view(), name="search-colleges"),
    path("applications/", ApplicationSearchView.as_view(), name="search-applications"),
    path("invoices/", InvoiceSearchView.as_view(), name="search-invoices"),
    path("guarantees/", GuaranteeSearchView.as_view(), name="search-guarantees"),
    path("job-seekers/", JobSeekerSearchView.as_view(), name="search-job-seekers"),
    path("recruiters/", RecruiterSearchView.as_view(), name="search-recruiters"),
    path("professors/", ProfessorSearchView.as_view(), name="search-professors"),
    path("admin/", AdminGlobalSearchView.as_view(), name="search-admin"),
]
