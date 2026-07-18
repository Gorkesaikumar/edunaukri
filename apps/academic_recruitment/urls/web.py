"""Web URL routes for Academic Recruitment."""

from django.urls import path

from apps.academic_recruitment.views.auth import (
    FacultyInstitutionLoginView,
    FacultyInstitutionSignupView,
    FacultyLoginView,
    FacultyProfessorLoginView,
    FacultyProfessorSignupView,
    FacultySignupCheckEmailView,
    FacultySignupView,
)
from apps.academic_recruitment.views.portal_redirects import (
    CollegePortalEntryRedirectView,
    ProfessorPortalEntryRedirectView,
)

urlpatterns = [
    path("login/", FacultyLoginView.as_view(), name="faculty_login"),
    path(
        "login/professor/",
        FacultyProfessorLoginView.as_view(),
        name="faculty_login_professor",
    ),
    path(
        "login/institution/",
        FacultyInstitutionLoginView.as_view(),
        name="faculty_login_institution",
    ),
    path("signup/", FacultySignupView.as_view(), name="faculty_signup"),
    path(
        "signup/professor/",
        FacultyProfessorSignupView.as_view(),
        name="faculty_signup_professor",
    ),
    path(
        "signup/institution/",
        FacultyInstitutionSignupView.as_view(),
        name="faculty_signup_institution",
    ),
    path(
        "signup/check-email/",
        FacultySignupCheckEmailView.as_view(),
        name="faculty_signup_check_email",
    ),
    path(
        "dashboard/professor/",
        ProfessorPortalEntryRedirectView.as_view(),
        name="faculty_professor_dashboard",
    ),
    path(
        "dashboard/institution/",
        CollegePortalEntryRedirectView.as_view(),
        name="faculty_institution_dashboard",
    ),
]
