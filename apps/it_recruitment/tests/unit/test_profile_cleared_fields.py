import pytest
from django.test import RequestFactory

from apps.accounts.models.it_user import ITUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_profile_manage_service import (
    JobSeekerProfileManageService,
)
from apps.it_recruitment.views.profile_api import JobSeekerProfileSectionAPIView
from apps.academic_recruitment.models import ProfessorProfile
from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.services.professor_profile_manage_service import (
    ProfessorProfileManageService,
)


@pytest.mark.django_db
class TestProfileClearedFields:
    """Test suite for clearing optional profile fields and ensuring persistence & consistency."""

    @pytest.fixture
    def seeker_user(self):
        user = ITUser.objects.create_user(
            email="nakul.test@edunaukri.com",
            password="TestPassword123!",
        )
        return user

    @pytest.fixture
    def seeker_profile(self, seeker_user):
        profile = JobSeekerProfile.objects.create(
            user=seeker_user,
            first_name="Nakul",
            last_name="Deshmukh",
            headline="Senior Developer Software Engineer",
            current_company="Acme Corp",
            current_location="Srinagar",
            experience_years=5,
            phone="9876543210",
            city="Srinagar",
            state="Jammu and Kashmir",
            country="India",
        )
        return profile

    def test_clear_last_name_persists_empty_string(self, seeker_profile, seeker_user):
        service = JobSeekerProfileManageService()

        payload = {
            "first_name": "Nakul",
            "last_name": "",
            "headline": "Senior Developer Software Engineer",
            "current_company": "",
            "current_location": "Srinagar",
            "experience_years": "",
        }

        updated_data = service.update_section(
            seeker_profile, "header", payload, actor_id=seeker_user.pk
        )

        seeker_profile.refresh_from_db()
        assert seeker_profile.last_name == ""
        assert seeker_profile.full_name == "Nakul"
        assert seeker_profile.current_company == ""
        assert seeker_profile.experience_years is None
        assert updated_data["full_name"] == "Nakul"
        assert updated_data["last_name"] == ""
        assert updated_data["current_company"] == ""

    def test_clearing_first_name_raises_validation_error(self, seeker_profile, seeker_user):
        service = JobSeekerProfileManageService()

        payload = {
            "first_name": "",
            "last_name": "Deshmukh",
        }

        with pytest.raises(ValidationException) as exc_info:
            service.update_section(seeker_profile, "header", payload, actor_id=seeker_user.pk)

        assert "First name is required" in str(exc_info.value)

    def test_clear_basic_information_optional_fields(self, seeker_profile, seeker_user):
        service = JobSeekerProfileManageService()

        payload = {
            "first_name": "Nakul",
            "last_name": "",
            "phone": "",
            "city": "",
            "state": "",
            "country": "",
        }

        service.update_section(seeker_profile, "basic", payload, actor_id=seeker_user.pk)

        seeker_profile.refresh_from_db()
        assert seeker_profile.last_name == ""
        assert seeker_profile.phone == ""
        assert seeker_profile.city == ""
        assert seeker_profile.state == ""
        assert seeker_profile.country == ""
        assert seeker_profile.full_name == "Nakul"

    def test_omitted_field_preserves_existing_value(self, seeker_profile, seeker_user):
        service = JobSeekerProfileManageService()

        # Update basic section omitting last_name
        payload = {
            "first_name": "Nakul",
            "city": "Mumbai",
        }

        service.update_section(seeker_profile, "basic", payload, actor_id=seeker_user.pk)

        seeker_profile.refresh_from_db()
        assert seeker_profile.city == "Mumbai"
        assert seeker_profile.last_name == "Deshmukh"  # Kept existing since omitted

    def test_profile_section_api_view_response_payload(self, seeker_profile, seeker_user):
        from apps.accounts.models.it_user_role import ITUserRole
        from apps.accounts.constants.enums import ITUserRoleType

        ITUserRole.objects.create(
            user=seeker_user, role=ITUserRoleType.JOB_SEEKER, is_primary=True
        )

        factory = RequestFactory()
        request = factory.patch(
            "/it/api/profile/sections/header/",
            data={
                "first_name": "Nakul",
                "last_name": "",
                "headline": "",
            },
            content_type="application/json",
        )
        request.user = seeker_user

        view = JobSeekerProfileSectionAPIView()
        response = view.patch(request, section="header")

        assert response.status_code == 200
        import json

        body = json.loads(response.content)
        assert body["success"] is True
        assert body["message"] == "Profile updated successfully."
        assert "data" in body
        assert "profile" in body
        assert body["data"]["full_name"] == "Nakul"
        assert body["profile"]["last_name"] == ""

    def test_professor_profile_cleared_fields(self):
        prof_user = ProfessorUser.objects.create_user(
            email="prof.test@edunaukri.com",
            password="TestPassword123!",
        )
        prof_profile = ProfessorProfile.objects.create(
            user=prof_user,
            first_name="Dr. Anil",
            last_name="Sharma",
            current_designation="Associate Professor",
            current_institution="IIT Bombay",
            teaching_experience_years=10,
        )

        service = ProfessorProfileManageService()

        # Clear last_name, designation, institution, teaching experience
        payload = {
            "first_name": "Dr. Anil",
            "last_name": "",
            "phone": "",
        }
        service.update_section(prof_profile, "basic", payload, actor_id=prof_user.pk)

        prof_profile.refresh_from_db()
        assert prof_profile.last_name == ""
        assert prof_profile.full_name == "Dr. Anil"

        prof_payload = {
            "current_designation": "",
            "current_institution": "",
            "teaching_experience_years": "",
        }
        service.update_section(prof_profile, "professional", prof_payload, actor_id=prof_user.pk)

        prof_profile.refresh_from_db()
        assert prof_profile.current_designation == ""
        assert prof_profile.current_institution == ""
        assert prof_profile.teaching_experience_years is None

    def test_account_settings_clears_last_name(self, seeker_profile, seeker_user):
        from apps.it_recruitment.services.account_settings_service import AccountSettingsService

        service = AccountSettingsService()
        data = {
            "first_name": "Nakul",
            "last_name": "",
            "phone": "9876543210",
        }
        res = service.update_account_info(seeker_profile, data, actor_id=seeker_user.pk, request_meta={})
        seeker_profile.refresh_from_db()

        assert seeker_profile.last_name == ""
        assert seeker_profile.full_name == "Nakul"
        assert res["full_name"] == "Nakul"
        assert res["last_name"] == ""
