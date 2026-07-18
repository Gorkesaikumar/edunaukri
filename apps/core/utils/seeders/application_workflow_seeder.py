from django.utils import timezone
from .base_seeder import BaseSeeder
from apps.jobs.models import JobPosting
from apps.faculty.models import FacultyVacancy
from apps.applications.models import (
    JobApplication,
    FacultyApplication,
    JobApplicationInterview,
)
from apps.it_recruitment.models import JobSeekerProfile
from apps.academic_recruitment.models import ProfessorProfile
from apps.applications.services.application_service import JobApplicationService
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.applications.services.application_workflow_service import (
    ApplicationWorkflowService,
)
from apps.applications.services.faculty_workflow_service import FacultyWorkflowService
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.accounts.models import AdminUser


class ApplicationWorkflowSeeder(BaseSeeder):
    def seed_it_applications(self):
        self.log("Seeding IT Applications...")
        jobs = list(JobPosting.objects.filter(is_deleted=False))
        seekers = list(JobSeekerProfile.objects.all())

        if not jobs or not seekers:
            return

        service = JobApplicationService()
        workflow = ApplicationWorkflowService()
        system_admin = AdminUser.objects.first()

        for job in jobs:
            # Pick 5-10 random seekers for this job
            num_apps = self.faker.random_int(5, 10)
            chosen_seekers = self.faker.random_elements(
                elements=seekers, length=num_apps, unique=True
            )

            for seeker in chosen_seekers:
                # 1. Apply
                application = service.apply(
                    job_posting=job,
                    job_seeker=seeker,
                    resume_file=seeker.resume_file,
                    expected_salary=self.faker.random_int(400000, 1000000),
                    cover_letter=self.faker.paragraph(nb_sentences=3),
                )

                # 2. Advance status randomly
                final_status = self.faker.random_element(
                    elements=[
                        JobApplicationStatus.APPLIED,
                        JobApplicationStatus.UNDER_REVIEW,
                        JobApplicationStatus.SHORTLISTED,
                        JobApplicationStatus.INTERVIEW_SCHEDULED,
                        JobApplicationStatus.OFFER_RELEASED,
                        JobApplicationStatus.HIRED,
                        JobApplicationStatus.REJECTED,
                    ]
                )

                # We need to progress the status logically, adhering to the state machine
                # applied -> under_review -> shortlisted -> interview_scheduled -> interview_completed -> offer_released -> offer_accepted -> hired

                # Helper to transition through intermediate states
                def step_it(state, notes=""):
                    workflow.update_status_for_actor(
                        application=application,
                        new_status=state,
                        actor=job.posted_by.user,
                        notes=notes,
                    )

                if final_status != JobApplicationStatus.APPLIED:
                    step_it(JobApplicationStatus.UNDER_REVIEW, "Moved to under review.")

                if final_status in [
                    JobApplicationStatus.SHORTLISTED,
                    JobApplicationStatus.INTERVIEW_SCHEDULED,
                    JobApplicationStatus.INTERVIEW_COMPLETED,
                    JobApplicationStatus.OFFER_RELEASED,
                    JobApplicationStatus.OFFER_ACCEPTED,
                    JobApplicationStatus.HIRED,
                ]:
                    step_it(JobApplicationStatus.SHORTLISTED, "Candidate shortlisted.")

                if final_status in [
                    JobApplicationStatus.INTERVIEW_SCHEDULED,
                    JobApplicationStatus.INTERVIEW_COMPLETED,
                    JobApplicationStatus.OFFER_RELEASED,
                    JobApplicationStatus.OFFER_ACCEPTED,
                    JobApplicationStatus.HIRED,
                ]:
                    step_it(
                        JobApplicationStatus.INTERVIEW_SCHEDULED, "Interview scheduled."
                    )

                    JobApplicationInterview.objects.create(
                        application=application,
                        interview_type=self.faker.random_element(
                            ["Technical Interview", "HR Round", "Final Round"]
                        ),
                        scheduled_at=self._get_random_future_date(),
                        meet_url="https://zoom.us/j/dummy",
                        instructions="Technical round instructions.",
                        scheduled_by_id=job.posted_by.user.id,
                    )

                if final_status in [
                    JobApplicationStatus.INTERVIEW_COMPLETED,
                    JobApplicationStatus.OFFER_RELEASED,
                    JobApplicationStatus.OFFER_ACCEPTED,
                    JobApplicationStatus.HIRED,
                ]:
                    step_it(
                        JobApplicationStatus.INTERVIEW_COMPLETED,
                        "Interview completed successfully.",
                    )

                if final_status in [
                    JobApplicationStatus.OFFER_RELEASED,
                    JobApplicationStatus.OFFER_ACCEPTED,
                    JobApplicationStatus.HIRED,
                ]:
                    step_it(
                        JobApplicationStatus.OFFER_RELEASED, "Candidate offered 12 LPA."
                    )

                if final_status in [
                    JobApplicationStatus.OFFER_ACCEPTED,
                    JobApplicationStatus.HIRED,
                ]:
                    workflow.update_status_for_actor(
                        application=application,
                        new_status=JobApplicationStatus.OFFER_ACCEPTED,
                        actor=seeker.user,
                        notes="Candidate accepted the offer.",
                    )

                if final_status == JobApplicationStatus.HIRED:
                    step_it(
                        JobApplicationStatus.HIRED, "Candidate accepted and joined."
                    )
                elif final_status == JobApplicationStatus.REJECTED:
                    # In this simulation, if the goal is rejected, we just reject from wherever it stopped.
                    # Wait, if we want random rejections, we should just reject at the end
                    step_it(
                        JobApplicationStatus.REJECTED, "Not a good fit at this time."
                    )

    def seed_faculty_applications(self):
        self.log("Seeding Faculty Applications...")
        vacancies = list(FacultyVacancy.objects.filter(is_deleted=False))
        professors = list(ProfessorProfile.objects.all())

        if not vacancies or not professors:
            return

        service = FacultyApplicationService()
        workflow = FacultyWorkflowService()

        for vacancy in vacancies:
            num_apps = self.faker.random_int(5, 10)
            chosen_profs = self.faker.random_elements(
                elements=professors, length=num_apps, unique=True
            )

            for professor in chosen_profs:
                application = service.apply(
                    vacancy=vacancy,
                    professor=professor,
                    cv_file=professor.cv_file,
                    expected_salary=self.faker.random_int(500000, 1200000),
                    cover_letter=self.faker.paragraph(nb_sentences=3),
                )

                final_status = self.faker.random_element(
                    elements=[
                        FacultyApplicationStatus.APPLIED,
                        FacultyApplicationStatus.DEPARTMENT_REVIEW,
                        FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                        FacultyApplicationStatus.JOINED,
                        FacultyApplicationStatus.REJECTED,
                    ]
                )

                # applied -> under_review -> academic_verification -> department_review -> principal_review -> management_approval -> interview_scheduled -> interview_completed -> offer_released -> offer_accepted -> joined
                def step_fac(state, notes=""):
                    workflow.update_status_for_actor(
                        application=application,
                        new_status=state,
                        actor=vacancy.posted_by,
                        notes=notes,
                    )

                if final_status != FacultyApplicationStatus.APPLIED:
                    step_fac(
                        FacultyApplicationStatus.UNDER_REVIEW,
                        "Application under review.",
                    )

                if final_status in [
                    FacultyApplicationStatus.DEPARTMENT_REVIEW,
                    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                    FacultyApplicationStatus.JOINED,
                ]:
                    step_fac(
                        FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                        "Verified academics.",
                    )
                    step_fac(
                        FacultyApplicationStatus.DEPARTMENT_REVIEW,
                        "Department reviewed.",
                    )

                if final_status in [
                    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                    FacultyApplicationStatus.JOINED,
                ]:
                    step_fac(
                        FacultyApplicationStatus.PRINCIPAL_REVIEW, "Principal reviewed."
                    )
                    step_fac(
                        FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                        "Management approved.",
                    )
                    step_fac(
                        FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                        "Invited for interview.",
                    )

                if final_status == FacultyApplicationStatus.JOINED:
                    step_fac(
                        FacultyApplicationStatus.INTERVIEW_COMPLETED,
                        "Interview completed.",
                    )
                    step_fac(FacultyApplicationStatus.OFFER_RELEASED, "Offer released.")
                    workflow.update_status_for_actor(
                        application=application,
                        new_status=FacultyApplicationStatus.OFFER_ACCEPTED,
                        actor=professor.user,
                        notes="Offer accepted.",
                    )
                    step_fac(FacultyApplicationStatus.JOINED, "Professor joined.")

                elif final_status == FacultyApplicationStatus.REJECTED:
                    step_fac(FacultyApplicationStatus.REJECTED, "Candidate rejected.")

    def seed_all(self):
        self.seed_it_applications()
        self.seed_faculty_applications()
