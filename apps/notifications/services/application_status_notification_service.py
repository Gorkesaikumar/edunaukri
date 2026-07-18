import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.notifications.constants.enums import NotificationChannel, NotificationStatus
from apps.notifications.repositories.notification_repository import NotificationRepository
from apps.authentication.services.portal_url_service import PortalURLService

logger = logging.getLogger(__name__)

class ApplicationStatusNotificationService:
    """
    Centralized service for generating application status change notifications
    and pushing real-time WebSocket updates to job seekers.
    """

    def __init__(self):
        self.notification_repository = NotificationRepository()
        self.channel_layer = get_channel_layer()

    def notify_status_change(self, application, domain: str, from_status: str, to_status: str):
        """
        Creates a notification and pushes a WebSocket event to the job seeker.
        Should be called inside `transaction.on_commit()` after a valid status transition.
        """
        if from_status == to_status:
            return

        # Determine the user ID and application details based on the domain
        if domain in [DomainType.FACULTY, "faculty"]:
            recipient_id = str(application.professor.user_id)
            recipient_domain = "professor"
            aggregate_type = EntityReferenceType.FACULTY_APPLICATION
            job_title = application.vacancy_title_snapshot
            institution_name = application.college_name_snapshot
            
            # Format message body
            body = self._format_faculty_message(to_status, job_title, institution_name)
            
            message_url = PortalURLService.professor(application.professor.user, "professor_messages")
            application_url = PortalURLService.professor(application.professor.user, "professor_application_detail", application_id=application.pk)
        
        elif domain in [DomainType.IT, "it"]:
            recipient_id = str(application.job_seeker.user_id)
            recipient_domain = "it"
            aggregate_type = EntityReferenceType.IT_JOB_APPLICATION
            job_title = application.job_title_snapshot
            institution_name = application.company_name_snapshot
            
            # Format message body
            body = self._format_it_message(to_status, job_title, institution_name)
            
            message_url = PortalURLService.jobseeker(application.job_seeker.user, "jobseeker_messages")
            application_url = PortalURLService.jobseeker(application.job_seeker.user, "jobseeker_application_detail", application_id=application.pk)
        else:
            logger.error(f"Unknown domain {domain} for application status notification.")
            return

        if not body:
            return

        # Check for duplicate notifications (prevent spamming same status)
        existing = self.notification_repository.get_queryset().filter(
            recipient_id=recipient_id,
            entity_type=aggregate_type,
            entity_id=application.pk,
            event_type="application.status_changed",
            payload__to_status=to_status
        ).order_by("-created_at").first()

        # If a very recent identical notification exists, skip
        if existing and (timezone.now() - existing.created_at).total_seconds() < 60:
            return

        payload = {
            "application_id": str(application.pk),
            "from_status": from_status,
            "to_status": to_status,
            "job_title": job_title,
            "institution_name": institution_name,
        }

        # Save Notification
        notification = self.notification_repository.create(
            recipient_domain=recipient_domain,
            recipient_id=recipient_id,
            channel=NotificationChannel.IN_APP,
            title="Application Update",
            body=body,
            event_type="application.status_changed",
            entity_type=aggregate_type,
            entity_id=application.pk,
            status=NotificationStatus.DELIVERED,
            payload=payload,
        )

        # Get unread count
        unread_count = self.get_unread_tracker_count(recipient_id, recipient_domain)

        # Generate persistent message if SELECTED
        if to_status == "selected":
            msg_event = "institution_message" if recipient_domain == "professor" else "recruiter_message"
            msg_title = "Congratulations! You've Been Selected"
            msg_body = f"Your application for {job_title} at {institution_name} has been selected. Check your messages for further updates from the recruiter."
            
            self.notification_repository.create(
                recipient_domain=recipient_domain,
                recipient_id=recipient_id,
                channel=NotificationChannel.IN_APP,
                title=msg_title,
                body=msg_body,
                event_type=msg_event,
                entity_type=aggregate_type,
                entity_id=application.pk,
                status=NotificationStatus.DELIVERED,
                payload=payload,
            )

        # Broadcast via WebSocket
        if self.channel_layer:
            group_name = f"user_{recipient_id}_notifications"
            message_payload = {
                "type": "notification.message",
                "message": {
                    "event": "application.status_changed",
                    "application_id": str(application.pk),
                    "new_status": to_status,
                    "unread_count": unread_count,
                    "title": "Application Update",
                    "body": body,
                    "notification_id": str(notification.pk)
                }
            }
            async_to_sync(self.channel_layer.group_send)(group_name, message_payload)
            
            if to_status == "selected":
                popup_payload = {
                    "type": "notification.message",
                    "message": {
                        "event": "application.selected_popup",
                        "application_id": str(application.pk),
                        "job_title": job_title,
                        "institution_name": institution_name,
                        "title": "Congratulations! You've Been Selected",
                        "body": msg_body,
                        "message_url": message_url,
                        "application_url": application_url
                    }
                }
                async_to_sync(self.channel_layer.group_send)(group_name, popup_payload)

    def _format_faculty_message(self, status, job_title, institution_name):
        if status == FacultyApplicationStatus.UNDER_REVIEW:
            return f"Your application for {job_title} at {institution_name} has been reviewed."
        elif status == FacultyApplicationStatus.SHORTLISTED:
            return f"Congratulations! You have been shortlisted for {job_title}."
        elif status == FacultyApplicationStatus.INTERVIEW_SCHEDULED:
            return f"Your interview for {job_title} has been scheduled."
        elif status == FacultyApplicationStatus.INTERVIEW_COMPLETED:
            return f"Your interview for {job_title} has been completed."
        elif status == FacultyApplicationStatus.SELECTED:
            return f"Congratulations! You have been selected for {job_title}."
        elif status == FacultyApplicationStatus.OFFER_RELEASED:
            return f"Your offer letter for {job_title} has been released."
        elif status == FacultyApplicationStatus.OFFER_ACCEPTED:
            return f"Your offer for {job_title} has been accepted successfully."
        elif status == FacultyApplicationStatus.JOINING_IN_PROGRESS:
            return f"Joining in progress for {job_title}."
        elif status == FacultyApplicationStatus.JOINED:
            return "Congratulations! Your joining status has been confirmed."
        elif status == FacultyApplicationStatus.REJECTED:
            return f"Your application for {job_title} was not selected."
        elif status == FacultyApplicationStatus.WITHDRAWN:
            return f"Your application for {job_title} has been withdrawn."
        return f"Your application for {job_title} is now {status.replace('_', ' ')}."

    def _format_it_message(self, status, job_title, company_name):
        if status == JobApplicationStatus.UNDER_REVIEW:
            return f"Your application for {job_title} at {company_name} has been reviewed."
        elif status == JobApplicationStatus.SHORTLISTED:
            return f"Congratulations! You have been shortlisted for {job_title}."
        elif status == JobApplicationStatus.INTERVIEW_SCHEDULED:
            return f"Your interview for {job_title} has been scheduled."
        elif status == JobApplicationStatus.INTERVIEW_COMPLETED:
            return f"Your interview for {job_title} has been completed."
        elif status == JobApplicationStatus.SELECTED:
            return f"Congratulations! You have been selected for {job_title}."
        elif status == JobApplicationStatus.OFFER_RELEASED:
            return f"Your offer letter for {job_title} has been released."
        elif status == JobApplicationStatus.OFFER_ACCEPTED:
            return f"Your offer for {job_title} has been accepted successfully."
        elif status == JobApplicationStatus.JOINING_IN_PROGRESS:
            return f"Joining in progress for {job_title}."
        elif status == JobApplicationStatus.HIRED:
            return "Congratulations! Your joining status has been confirmed."
        elif status == JobApplicationStatus.REJECTED:
            return f"Your application for {job_title} was not selected."
        elif status == JobApplicationStatus.WITHDRAWN:
            return f"Your application for {job_title} has been withdrawn."
        return f"Your application for {job_title} is now {status.replace('_', ' ')}."

    @classmethod
    def get_unread_tracker_count(cls, user_id, recipient_domain):
        """Returns the number of unread application status notifications for a user."""
        from apps.notifications.models.notification import Notification
        return Notification.objects.filter(
            recipient_id=user_id,
            recipient_domain=recipient_domain,
            event_type="application.status_changed",
            is_read=False
        ).count()
