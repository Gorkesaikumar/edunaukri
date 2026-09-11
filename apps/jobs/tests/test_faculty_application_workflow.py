from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.college_user import CollegeUser
from apps.colleges.models.college import College
from apps.academic_recruitment.models.professor import ProfessorProfile
from apps.faculty.models.vacancy import FacultyVacancy
from apps.applications.models.application import FacultyApplication
from apps.jobs.services.job_marketplace_service import JobMarketplaceService
from apps.authentication.services.web_jwt_service import WebJWTService


class FacultyApplicationWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create College
        self.college = College.objects.create(
            name="Sahasra Degree & PG College",
            slug="sahasra-college",
            institution_type="arts_science",
        )

        # Create College User (posted_by)
        self.college_user = CollegeUser.objects.create_user(
            email="recruiter@sahasra.edu",
            password="password123",
        )

        # Create Faculty Vacancy
        self.vacancy = FacultyVacancy.objects.create(
            college=self.college,
            posted_by=self.college_user,
            title="Assistant Professor – Data Analytics & Commerce",
            status="published",
            slug="assistant-professor-data-analytics-commerce",
        )

        # Create Professor User & Profile
        self.professor_user = ProfessorUser.objects.create_user(
            email="sai.krishna@example.com",
            password="password123",
        )
        self.professor_profile = ProfessorProfile.objects.create(
            user=self.professor_user,
        )

        # Create IT User
        self.it_user = ITUser.objects.create_user(
            email="it.seeker@example.com",
            password="password123",
        )

    def login_user(self, user, domain):
        self.client.force_login(user)
        jwt_service = WebJWTService()
        access_token, _, _ = jwt_service.issue_tokens(user=user, domain=domain)
        self.client.cookies[jwt_service.access_cookie] = access_token

    def test_anonymous_user_sees_sign_in_to_apply_on_job_detail(self):
        url = reverse("marketplace_vacancy_detail", kwargs={"job_id": str(self.vacancy.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to Apply")
        self.assertNotContains(response, "Apply Now")

    def test_authenticated_eligible_professor_sees_apply_now(self):
        self.login_user(self.professor_user, "professor")
        url = reverse("marketplace_vacancy_detail", kwargs={"job_id": str(self.vacancy.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sign in to Apply")
        self.assertContains(response, "Apply Now")

    def test_already_applied_professor_sees_applied_state(self):
        # Create application
        FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor_profile,
            status="submitted",
        )
        self.login_user(self.professor_user, "professor")
        url = reverse("marketplace_vacancy_detail", kwargs={"job_id": str(self.vacancy.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sign in to Apply")
        self.assertContains(response, "Applied")

    def test_authenticated_non_faculty_user_does_not_see_sign_in_to_apply(self):
        self.login_user(self.it_user, "it")
        url = reverse("marketplace_vacancy_detail", kwargs={"job_id": str(self.vacancy.pk)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sign in to Apply")

    def test_job_marketplace_service_detail_state(self):
        detail = JobMarketplaceService().get_job_detail(str(self.vacancy.pk), domain="faculty", user=self.professor_user)
        self.assertIsNotNone(detail)
        self.assertTrue(detail["is_faculty_seeker"])
        self.assertFalse(detail["card"].has_applied)
        self.assertIsNotNone(detail["card"].apply_url)
