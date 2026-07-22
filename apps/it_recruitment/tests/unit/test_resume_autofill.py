"""Unit tests for AI Resume Analysis Apply to Profile mapping, synchronizer, service, and API contract."""

from unittest.mock import MagicMock

from django.test import RequestFactory, TestCase

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.it_user_role import ITUserRole
from apps.it_recruitment.models import (
    JobSeekerCertification,
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProfile,
    JobSeekerProject,
)
from apps.it_recruitment.services.resume_profile_mapper import (
    MappedProfileData,
    ResumeProfileMapper,
    sanitize_phone,
    sanitize_text,
    sanitize_url,
)
from apps.it_recruitment.services.resume_profile_synchronizer import (
    ResumeProfileSynchronizer,
)
from apps.it_recruitment.views.resume_api import JobSeekerResumeAutofillAPIView
from apps.jobs.models import JobSeekerSkill


class ResumeProfileMapperTestCase(TestCase):
    """Test sanitization and mapping of AI extracted JSON."""

    def test_sanitize_text_filters_sentinels(self):
        self.assertEqual(sanitize_text("Unknown"), "")
        self.assertEqual(sanitize_text("N/A"), "")
        self.assertEqual(sanitize_text("null"), "")
        self.assertEqual(sanitize_text(None), "")
        self.assertEqual(sanitize_text("  Python Developer  "), "Python Developer")

    def test_sanitize_url(self):
        self.assertEqual(sanitize_url("invalid_url"), "")
        self.assertEqual(sanitize_url("github.com/test"), "https://github.com/test")
        self.assertEqual(
            sanitize_url("https://linkedin.com/in/test"), "https://linkedin.com/in/test"
        )

    def test_sanitize_phone(self):
        self.assertEqual(sanitize_phone("123"), "")
        self.assertEqual(sanitize_phone("+91 9876543210"), "+919876543210")

    def test_sanitize_date(self):
        from datetime import date
        from apps.it_recruitment.services.resume_profile_mapper import sanitize_date
        self.assertIsNone(sanitize_date("invalid"))
        self.assertEqual(sanitize_date("2023-05-15"), date(2023, 5, 15))
        self.assertEqual(sanitize_date("Jan 2022"), date(2022, 1, 1))
        self.assertEqual(sanitize_date("2020"), date(2020, 1, 1))

    def test_map_parsed_data_complete(self):
        parsed = {
            "name": "Jane Doe",
            "phone": "+91 9876543210",
            "summary": "Senior Python Developer",
            "headline": "Tech Lead",
            "location": "Hyderabad",
            "experience_years": 5,
            "skills": ["Python", "Django", "Docker", "Python"],
            "languages": ["English", "Hindi"],
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "github_url": "github.com/janedoe",
            "experience": [
                {
                    "company_name": "Acme Corp",
                    "title": "Software Engineer",
                    "location": "Hyderabad",
                    "description": "Built REST APIs",
                }
            ],
            "education": [
                {
                    "institution": "ABC Institute of Technology",
                    "degree": "B.Tech Computer Science",
                    "passing_year": 2020,
                    "cgpa": 8.5,
                }
            ],
            "projects": [
                {
                    "title": "E-Commerce Engine",
                    "description": "Django microservices",
                    "technologies": ["Django", "PostgreSQL"],
                }
            ],
            "certifications": [
                {
                    "name": "AWS Certified Developer",
                    "issuing_organization": "Amazon Web Services",
                }
            ],
        }

        mapped = ResumeProfileMapper().map_parsed_data(parsed)

        self.assertEqual(mapped.profile_fields["phone"], "+919876543210")
        self.assertEqual(mapped.profile_fields["summary"], "Senior Python Developer")
        self.assertEqual(mapped.profile_fields["current_location"], "Hyderabad")
        self.assertEqual(mapped.profile_fields["experience_years"], 5)
        self.assertEqual(mapped.skills, ["Python", "Django", "Docker"])
        self.assertEqual(len(mapped.experiences), 1)
        self.assertEqual(mapped.experiences[0]["company_name"], "Acme Corp")
        self.assertEqual(len(mapped.education), 1)
        self.assertEqual(mapped.education[0]["institution"], "ABC Institute of Technology")
        self.assertEqual(len(mapped.projects), 1)
        self.assertEqual(mapped.projects[0]["title"], "E-Commerce Engine")
        self.assertEqual(len(mapped.certifications), 1)
        self.assertEqual(mapped.certifications[0]["name"], "AWS Certified Developer")


class ResumeProfileSynchronizerTestCase(TestCase):
    """Test smart merging into profile models."""

    def setUp(self):
        self.user = ITUser.objects.create_user(
            email="seeker1@example.com", password="password123"
        )
        ITUserRole.objects.create(
            user=self.user, role=ITUserRoleType.JOB_SEEKER, is_primary=True
        )
        self.profile = JobSeekerProfile.objects.create(
            user=self.user,
            first_name="Jane",
            last_name="Doe",
            phone="",
            summary="",
            experience_years=None,
        )

    def test_sync_preserves_existing_data_and_fills_empty(self):
        self.profile.headline = "Existing Headline"
        self.profile.save()

        mapped = MappedProfileData(
            profile_fields={
                "phone": "+919876543210",
                "headline": "New AI Headline",
                "summary": "New AI Summary",
            },
            skills=["Python", "Django"],
        )

        updated_sections = ResumeProfileSynchronizer().sync(
            self.profile, mapped, actor_id=self.user.pk
        )

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.headline, "Existing Headline")
        self.assertEqual(self.profile.summary, "New AI Summary")
        self.assertEqual(self.profile.phone, "+919876543210")
        self.assertIn("Personal Information", updated_sections)
        self.assertIn("Skills", updated_sections)

        seeker_skills = list(
            JobSeekerSkill.objects.filter(
                job_seeker=self.profile, is_deleted=False
            ).values_list("skill__name", flat=True)
        )
        self.assertIn("Python", seeker_skills)
        self.assertIn("Django", seeker_skills)

    def test_sync_deduplicates_nested_collections(self):
        mapped = MappedProfileData(
            experiences=[
                {
                    "company_name": "Tech Corp",
                    "title": "Developer",
                    "description": "Phase 1",
                }
            ],
            education=[
                {"institution": "Tech Uni", "degree": "B.Tech", "passing_year": 2021}
            ],
            projects=[{"title": "Portal App", "description": "Django project"}],
            certifications=[
                {"name": "AWS Solutions Architect", "issuing_organization": "AWS"}
            ],
        )

        sections1 = ResumeProfileSynchronizer().sync(
            self.profile, mapped, actor_id=self.user.pk
        )
        self.assertEqual(len(sections1), 4)

        sections2 = ResumeProfileSynchronizer().sync(
            self.profile, mapped, actor_id=self.user.pk
        )
        self.assertEqual(len(sections2), 0)

        self.assertEqual(
            JobSeekerExperience.objects.filter(job_seeker=self.profile).count(), 1
        )
        self.assertEqual(
            JobSeekerEducation.objects.filter(job_seeker=self.profile).count(), 1
        )
        self.assertEqual(
            JobSeekerProject.objects.filter(job_seeker=self.profile).count(), 1
        )
        self.assertEqual(
            JobSeekerCertification.objects.filter(job_seeker=self.profile).count(), 1
        )


class JobSeekerResumeAutofillAPIViewTestCase(TestCase):
    """Test API endpoint response contract and error handling."""

    def setUp(self):
        self.rf = RequestFactory()
        self.user = ITUser.objects.create_user(
            email="seeker_api@example.com", password="password123"
        )
        ITUserRole.objects.create(
            user=self.user, role=ITUserRoleType.JOB_SEEKER, is_primary=True
        )
        self.profile = JobSeekerProfile.objects.create(
            user=self.user, first_name="API", last_name="User"
        )

    def test_missing_resume_returns_400_json_contract(self):
        import json
        req = self.rf.post("/it/jobseeker/api/resume/autofill/")
        req.user = self.user
        req._dont_enforce_csrf_checks = True

        view = JobSeekerResumeAutofillAPIView.as_view()
        resp = view(req)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp["Content-Type"], "application/json")
        data = json.loads(resp.content)
        self.assertFalse(data["success"])
        self.assertIn("Upload a resume", data["message"])
        self.assertIn("detail", data["errors"])
