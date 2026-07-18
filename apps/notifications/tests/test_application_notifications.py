import pytest
import unittest.mock
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.utils import timezone
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.notifications.services.application_status_notification_service import ApplicationStatusNotificationService
from apps.notifications.models.notification import Notification
from apps.core.constants.enums import DomainType

pytestmark = pytest.mark.django_db


@pytest.fixture
def it_application_mock():
    mock_app = MagicMock()
    mock_app.pk = "11111111-1111-1111-1111-111111111111"
    mock_app.job_seeker.user_id = "22222222-2222-2222-2222-222222222222"
    mock_app.job_title_snapshot = "Python Developer"
    mock_app.company_name_snapshot = "Tech Corp"
    return mock_app


@pytest.fixture
def faculty_application_mock():
    mock_app = MagicMock()
    mock_app.pk = "33333333-3333-3333-3333-333333333333"
    mock_app.professor.user_id = "44444444-4444-4444-4444-444444444444"
    mock_app.vacancy_title_snapshot = "Physics Lecturer"
    mock_app.college_name_snapshot = "Soumya Institution"
    return mock_app


class TestApplicationStatusNotificationService:
    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_it_domain_isolation(self, mock_async, mock_portal, it_application_mock):
        service = ApplicationStatusNotificationService()
        service.notify_status_change(it_application_mock, "it", "applied", JobApplicationStatus.SHORTLISTED)
        
        notifs = Notification.objects.filter(recipient_domain="it")
        assert notifs.count() == 1
        assert "shortlisted" in notifs.first().body.lower()

    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_faculty_domain_isolation(self, mock_async, mock_portal, faculty_application_mock):
        service = ApplicationStatusNotificationService()
        service.notify_status_change(faculty_application_mock, "faculty", "applied", FacultyApplicationStatus.SHORTLISTED)
        
        notifs = Notification.objects.filter(recipient_domain="professor")
        assert notifs.count() == 1
        assert "shortlisted" in notifs.first().body.lower()

    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_events_generation(self, mock_async, mock_portal, it_application_mock):
        service = ApplicationStatusNotificationService()
        
        events = [
            ("applied", JobApplicationStatus.SHORTLISTED, "shortlisted"),
            (JobApplicationStatus.SHORTLISTED, JobApplicationStatus.INTERVIEW_SCHEDULED, "scheduled"),
            (JobApplicationStatus.INTERVIEW_SCHEDULED, JobApplicationStatus.SELECTED, "selected"),
            (JobApplicationStatus.SELECTED, JobApplicationStatus.OFFER_RELEASED, "released"),
            (JobApplicationStatus.OFFER_RELEASED, JobApplicationStatus.OFFER_ACCEPTED, "accepted"),
            (JobApplicationStatus.OFFER_ACCEPTED, JobApplicationStatus.HIRED, "confirmed"),
            ("applied", JobApplicationStatus.REJECTED, "not selected"),
        ]
        
        for from_status, to_status, keyword in events:
            service.notify_status_change(it_application_mock, "it", from_status, to_status)
            notif = Notification.objects.order_by("-created_at").first()
            assert keyword in notif.body.lower()

    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_duplicate_notification_prevention(self, mock_async, mock_portal, it_application_mock):
        service = ApplicationStatusNotificationService()
        service.notify_status_change(it_application_mock, "it", "applied", JobApplicationStatus.SHORTLISTED)
        count_before = Notification.objects.count()
        
        # Call again with same transition
        service.notify_status_change(it_application_mock, "it", "applied", JobApplicationStatus.SHORTLISTED)
        assert Notification.objects.count() == count_before

    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_correct_user_receives_notification(self, mock_async, mock_portal, it_application_mock):
        service = ApplicationStatusNotificationService()
        service.notify_status_change(it_application_mock, "it", "applied", JobApplicationStatus.SHORTLISTED)
        
        # Verify websocket group name is specific to the user
        expected_group = f"user_{it_application_mock.job_seeker.user_id}_notifications"
        mock_async.return_value.assert_called_with(expected_group, unittest.mock.ANY)

    def test_invalid_status_transition_does_not_trigger(self, it_application_mock):
        # Service ignores if from_status == to_status
        service = ApplicationStatusNotificationService()
        service.notify_status_change(it_application_mock, "it", "applied", "applied")
        assert Notification.objects.count() == 0

    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_tracker_unread_count_increments(self, mock_async, mock_portal, it_application_mock):
        service = ApplicationStatusNotificationService()
        user_id = str(it_application_mock.job_seeker.user_id)
        
        count_before = service.get_unread_tracker_count(user_id, "it")
        service.notify_status_change(it_application_mock, "it", "applied", JobApplicationStatus.SHORTLISTED)
        
        assert service.get_unread_tracker_count(user_id, "it") == count_before + 1

    @patch("apps.notifications.services.application_status_notification_service.PortalURLService")
    @patch("apps.notifications.services.application_status_notification_service.async_to_sync")
    def test_selected_status_creates_persistent_message(self, mock_async, mock_portal, it_application_mock):
        service = ApplicationStatusNotificationService()
        
        # Verify no recruiter_message notifications exist initially
        initial_count = Notification.objects.filter(event_type="recruiter_message").count()
        assert initial_count == 0
        
        # Trigger SELECTED status
        service.notify_status_change(it_application_mock, "it", JobApplicationStatus.INTERVIEW_COMPLETED, JobApplicationStatus.SELECTED)
        
        # Verify a new persistent message was created
        msg_notifs = Notification.objects.filter(event_type="recruiter_message")
        assert msg_notifs.count() == 1
        
        msg = msg_notifs.first()
        assert "Congratulations! You've Been Selected" in msg.title
        assert "has been selected" in msg.body
        
        # Verify two websocket events were fired (one for status update, one for selection popup)
        assert mock_async.return_value.call_count == 2

