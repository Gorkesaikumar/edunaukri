import uuid
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models.professor import ProfessorProfile
from apps.applications.models import FacultyApplication
from apps.colleges.models import College
from apps.faculty.models import FacultyVacancy


class SoftDeleteProtectedArchitectureTestCase(TestCase):
    def setUp(self):
        # Create prerequisite objects for testing
        self.college = College.objects.create(
            name=f"Test College {uuid.uuid4().hex[:6]}",
            slug=f"test-college-{uuid.uuid4().hex[:6]}",
        )
        self.college_user = CollegeUser.objects.create(
            email=f"college_user_{uuid.uuid4().hex[:6]}@example.com",
            is_active=True,
        )
        self.prof_user = ProfessorUser.objects.create(
            email=f"prof_user_{uuid.uuid4().hex[:6]}@example.com",
            is_active=True,
        )
        self.professor = ProfessorProfile.objects.create(
            user=self.prof_user,
            first_name="Jane",
            last_name="Doe",
        )
        self.vacancy = FacultyVacancy.objects.create(
            college=self.college,
            posted_by=self.college_user,
            title="Assistant Professor of Computer Science",
            slug=f"assistant-prof-{uuid.uuid4().hex[:6]}",
            college_name_snapshot=self.college.name,
        )

    def test_deleting_active_faculty_application_performs_soft_delete(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        self.assertFalse(app.is_deleted)
        self.assertIsNone(app.deleted_at)

        app.delete()

        app.refresh_from_db()
        self.assertTrue(app.is_deleted)
        self.assertIsNotNone(app.deleted_at)

    def test_soft_deleted_application_hidden_from_normal_queries(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()

        active_apps = FacultyApplication.objects.filter(pk=app.pk)
        self.assertFalse(active_apps.exists())

    def test_soft_deleted_application_accessible_via_all_objects(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()

        all_apps = FacultyApplication.all_objects.filter(pk=app.pk)
        self.assertTrue(all_apps.exists())
        fetched_app = all_apps.first()
        self.assertTrue(fetched_app.is_deleted)

    def test_deleting_vacancy_with_active_application_is_blocked(self):
        FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )

        with self.assertRaises(ProtectedError):
            self.vacancy.hard_delete()

    def test_deleting_vacancy_with_only_soft_deleted_applications_succeeds(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()

        # Hard deleting the vacancy should purge the soft-deleted application and succeed
        self.vacancy.hard_delete()

        self.assertFalse(FacultyVacancy.all_objects.filter(pk=self.vacancy.pk).exists())
        self.assertFalse(FacultyApplication.all_objects.filter(pk=app.pk).exists())

    def test_soft_deleting_vacancy_with_soft_deleted_applications_succeeds(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()

        # Soft-deleting the vacancy purges soft-deleted applications and soft-deletes the vacancy
        self.vacancy.delete()

        self.vacancy.refresh_from_db()
        self.assertTrue(self.vacancy.is_deleted)
        self.assertFalse(FacultyApplication.all_objects.filter(pk=app.pk).exists())

    def test_deleting_college_user_with_active_vacancies_is_blocked(self):
        FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )

        with self.assertRaises(ProtectedError):
            self.college_user.hard_delete()

    def test_deleting_college_user_after_vacancies_and_applications_soft_deleted_succeeds(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()
        self.vacancy.delete()

        # Hard-deleting CollegeUser should purge soft-deleted vacancies/applications and succeed
        self.college_user.hard_delete()

        self.assertFalse(CollegeUser.all_objects.filter(pk=self.college_user.pk).exists())
        self.assertFalse(FacultyVacancy.all_objects.filter(pk=self.vacancy.pk).exists())
        self.assertFalse(FacultyApplication.all_objects.filter(pk=app.pk).exists())

    def test_no_orphaned_records_created(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()
        vacancy_id = self.vacancy.pk

        self.vacancy.hard_delete()

        # Ensure no application rows exist in DB pointing to the deleted vacancy
        orphaned = FacultyApplication.all_objects.filter(vacancy_id=vacancy_id)
        self.assertFalse(orphaned.exists())

    def test_repeated_deletion_attempts_handled_safely(self):
        app = FacultyApplication.objects.create(
            vacancy=self.vacancy,
            professor=self.professor,
            college=self.college,
            applicant_name_snapshot="Jane Doe",
            vacancy_title_snapshot=self.vacancy.title,
            college_name_snapshot=self.college.name,
        )
        app.delete()
        # Second delete attempt should be idempotent
        app.delete()
        self.assertTrue(app.is_deleted)

        app.hard_delete()
        # Hard delete on already removed object should be safe or raise ObjectDoesNotExist if re-fetched
        self.assertFalse(FacultyApplication.all_objects.filter(pk=app.pk).exists())
