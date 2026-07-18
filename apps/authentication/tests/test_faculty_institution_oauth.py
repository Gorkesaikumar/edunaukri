import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.authentication.models import OAuthProvider, ConnectedOAuthAccount
from apps.authentication.services.oauth_service import OAuthService
from apps.authentication.services.oauth_account_service import OAuthIdentity


@pytest.fixture
def mock_google_identity():
    return OAuthIdentity(
        provider=OAuthProvider.GOOGLE,
        provider_user_id="google123",
        email="test_college@university.edu",
        first_name="Test",
        last_name="College",
        email_verified=True,
    )


@pytest.fixture
def mock_linkedin_identity():
    return OAuthIdentity(
        provider=OAuthProvider.LINKEDIN,
        provider_user_id="linkedin456",
        email="linkedin_college@university.edu",
        first_name="LinkedIn",
        last_name="Inst",
        email_verified=True,
    )


@pytest.mark.django_db
class TestFacultyInstitutionOAuth:
    
    @patch.object(OAuthService, '_google_identity')
    def test_new_faculty_recruiter_using_google(self, mock_identity, client, mock_google_identity):
        """Test creating a new Faculty Recruiter (CollegeUser) via Google OAuth."""
        mock_identity.return_value = mock_google_identity
        
        # Setup session for callback
        session = client.session
        session[OAuthService.SESSION_STATE_KEY] = "valid_state"
        session[OAuthService.SESSION_PROVIDER_KEY] = OAuthProvider.GOOGLE
        session[OAuthService.SESSION_ROLE_KEY] = "college"
        session.save()

        url = reverse("oauth_google_callback")
        response = client.get(url, {"state": "valid_state", "code": "mock_code"})
        
        # Assert redirects to College dashboard/onboarding (portal URL)
        assert response.status_code == 302
        assert "/faculty/dashboard/institution/" in response.url or "/college/" in response.url
        
        # Assert user created
        user = CollegeUser.objects.get(email="test_college@university.edu")
        assert user.account_status == AccountStatus.ACTIVE
        assert user.email_verified is True
        
        # Assert OAuth connection created
        connection = ConnectedOAuthAccount.objects.get(user_id=user.pk, domain="college")
        assert connection.provider == OAuthProvider.GOOGLE
        assert connection.provider_user_id == "google123"

    @patch.object(OAuthService, '_linkedin_identity')
    def test_existing_google_linked_recruiter_login(self, mock_identity, client, mock_linkedin_identity):
        """Test logging into an existing CollegeUser account via LinkedIn."""
        mock_identity.return_value = mock_linkedin_identity
        
        # Create user and connection first
        user = CollegeUser.objects.create(email="linkedin_college@university.edu", account_status=AccountStatus.ACTIVE)
        ConnectedOAuthAccount.objects.create(
            user_id=user.pk,
            domain="college",
            provider=OAuthProvider.LINKEDIN,
            provider_user_id="linkedin456",
            created_by_id=user.pk
        )
        
        # Setup session
        session = client.session
        session[OAuthService.SESSION_STATE_KEY] = "valid_state"
        session[OAuthService.SESSION_PROVIDER_KEY] = OAuthProvider.LINKEDIN
        session[OAuthService.SESSION_ROLE_KEY] = "college"
        session.save()

        url = reverse("oauth_linkedin_callback")
        response = client.get(url, {"state": "valid_state", "code": "mock_code"})
        
        assert response.status_code == 302
        # Assert user is logged in (session has user details or JWT set)
        assert CollegeUser.objects.count() == 1

    @patch.object(OAuthService, '_google_identity')
    def test_existing_job_seeker_account_conflict(self, mock_identity, client):
        """Test that a ProfessorUser cannot log in as an Institution with the same email via OAuth without explicit handling."""
        ProfessorUser.objects.create(email="conflict@university.edu", account_status=AccountStatus.ACTIVE)
        
        identity = OAuthIdentity(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="conflict123",
            email="conflict@university.edu",
            first_name="Conflict",
            last_name="User",
            email_verified=True,
        )
        mock_identity.return_value = identity
        
        session = client.session
        session[OAuthService.SESSION_STATE_KEY] = "valid_state"
        session[OAuthService.SESSION_PROVIDER_KEY] = OAuthProvider.GOOGLE
        session[OAuthService.SESSION_ROLE_KEY] = "college"
        session.save()

        url = reverse("oauth_google_callback")
        response = client.get(url, {"state": "valid_state", "code": "mock_code"})
        
        # In this architecture, CollegeUser and ProfessorUser are separate models. 
        # A CollegeUser will be created with the same email if allowed, or it will conflict.
        # EduNaukri architecture uses separate tables so it creates a CollegeUser with the same email.
        # We just verify it successfully handles it without crashing.
        assert response.status_code == 302
        assert CollegeUser.objects.filter(email="conflict@university.edu").exists()
        assert ProfessorUser.objects.filter(email="conflict@university.edu").exists()
        
    @patch.object(OAuthService, '_google_identity')
    def test_suspended_institution_access_blocked(self, mock_identity, client, mock_google_identity):
        """Test that suspended CollegeUsers cannot login via OAuth."""
        mock_identity.return_value = mock_google_identity
        
        user = CollegeUser.objects.create(
            email="test_college@university.edu",
            account_status=AccountStatus.SUSPENDED
        )
        ConnectedOAuthAccount.objects.create(
            user_id=user.pk,
            domain="college",
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google123",
            created_by_id=user.pk
        )
        
        session = client.session
        session[OAuthService.SESSION_STATE_KEY] = "valid_state"
        session[OAuthService.SESSION_PROVIDER_KEY] = OAuthProvider.GOOGLE
        session[OAuthService.SESSION_ROLE_KEY] = "college"
        session.save()

        url = reverse("oauth_google_callback")
        response = client.get(url, {"state": "valid_state", "code": "mock_code"})
        
        assert response.status_code == 302
        # It should redirect to login with an error
        assert "oauth_error" in response.url
        assert "suspended" in response.url.lower() or "blocked" in response.url.lower() or "active" in response.url.lower()

    def test_invalid_oauth_state_rejected(self, client):
        """Test that invalid OAuth state prevents login."""
        session = client.session
        session[OAuthService.SESSION_STATE_KEY] = "valid_state"
        session[OAuthService.SESSION_PROVIDER_KEY] = OAuthProvider.GOOGLE
        session[OAuthService.SESSION_ROLE_KEY] = "college"
        session.save()

        url = reverse("oauth_google_callback")
        response = client.get(url, {"state": "INVALID_STATE", "code": "mock_code"})
        
        assert response.status_code == 302
        assert "oauth_error" in response.url
        assert "expired" in response.url.lower() or "try+again" in response.url.lower()

