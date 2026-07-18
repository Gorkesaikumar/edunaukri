import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import ITUser, ProfessorUser, CollegeUser
from apps.jobs.models import JobPosting
from apps.faculty.models import FacultyVacancy
from apps.companies.models import Company
from apps.colleges.models import College
from apps.applications.models import JobApplication, FacultyApplication
from apps.invoices.models import Invoice
from apps.guarantee_claims.models import GuaranteeClaim
from apps.documents.models import StoredFile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Safely deletes all seeded demo data while preserving system configurations and admins."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Force deletion without prompt"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            self.stdout.write(
                self.style.ERROR(
                    "You must use --force to run this in production! Aborting."
                )
            )
            return

        if not options["force"]:
            confirm = input(
                "This will WIPE all Job Seekers, Recruiters, Colleges, Jobs, Applications, Invoices, and Claims. Type 'YES' to confirm: "
            )
            if confirm != "YES":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        self.stdout.write("Starting to clear demo data...")

        def hard_delete(model):
            try:
                if hasattr(model, "all_objects") and hasattr(
                    model.all_objects.all(), "hard_delete"
                ):
                    model.all_objects.all().hard_delete()
                else:
                    model.objects.all().delete()
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Failed to hard delete {model.__name__}: {e}")
                )
                model.objects.all().delete()

        # 1. Clear Invoices & Claims
        hard_delete(Invoice)
        hard_delete(GuaranteeClaim)

        # 2. Clear Applications
        hard_delete(JobApplication)
        hard_delete(FacultyApplication)

        # 3. Clear Postings
        hard_delete(JobPosting)
        hard_delete(FacultyVacancy)

        # 4. Clear Companies & Colleges
        hard_delete(Company)
        hard_delete(College)

        # 5. Clear Users
        # Ensure we delete the profiles first to remove the protected foreign keys
        from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
        from apps.academic_recruitment.models import ProfessorProfile

        hard_delete(JobSeekerProfile)
        hard_delete(RecruiterProfile)
        hard_delete(ProfessorProfile)

        hard_delete(ITUser)
        hard_delete(ProfessorUser)
        hard_delete(CollegeUser)

        # 6. Clear StoredFiles
        hard_delete(StoredFile)

        self.stdout.write(
            self.style.SUCCESS("All demo data has been successfully cleared!")
        )
