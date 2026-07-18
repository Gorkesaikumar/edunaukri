import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import AdminUser

from apps.core.utils.seeders.account_seeder import AccountSeeder
from apps.core.utils.seeders.job_posting_seeder import JobPostingSeeder
from apps.core.utils.seeders.file_asset_seeder import FileAssetSeeder
from apps.core.utils.seeders.application_workflow_seeder import (
    ApplicationWorkflowSeeder,
)
from apps.core.utils.seeders.billing_claims_seeder import BillingClaimsSeeder
from apps.billing.models import FeeSchedule
from apps.billing.constants.enums import FeeType
from apps.core.constants.enums import DomainType
from decimal import Decimal

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seeds the database with massive realistic demo data for end-to-end testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="DemoPassword123!@#",
            help="Password for all demo users",
        )
        parser.add_argument("--force", action="store_true", help="Bypass confirmations")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Massive Demo Data Seeder..."))
        password = options["password"]

        # Ensure SuperAdmin exists
        if not AdminUser.objects.filter(email="superadmin@demo.edunaukri").exists():
            AdminUser.objects.create_superuser("superadmin@demo.edunaukri", password)
            self.stdout.write(self.style.SUCCESS("Created superadmin@demo.edunaukri"))

        # Ensure FeeSchedules exist
        if not FeeSchedule.objects.filter(domain=DomainType.IT).exists():
            FeeSchedule.objects.create(
                domain=DomainType.IT,
                name="IT Standard Fee",
                fee_type=FeeType.FIXED,
                fixed_amount=Decimal("50000.00"),
            )
        if not FeeSchedule.objects.filter(domain=DomainType.FACULTY).exists():
            FeeSchedule.objects.create(
                domain=DomainType.FACULTY,
                name="Faculty Standard Fee",
                fee_type=FeeType.FIXED,
                fixed_amount=Decimal("25000.00"),
            )

        # Phase 1: Accounts (Seekers, Recruiters, Colleges)
        account_seeder = AccountSeeder(password=password)
        account_seeder.seed_all()

        # Phase 2: Dummy Files & Resumes (Must exist before applications)
        asset_seeder = FileAssetSeeder(password=password)
        asset_seeder.seed_all()

        # Phase 3: Job Postings
        job_seeder = JobPostingSeeder(password=password)
        job_seeder.seed_all()

        # Phase 4: Applications & Workflow (Interviews, Offers, Hired -> Triggers Billing)
        workflow_seeder = ApplicationWorkflowSeeder(password=password)
        workflow_seeder.seed_all()

        # Process outbox events so invoices are generated from HIRED states
        self.stdout.write(self.style.WARNING("Processing billing outbox events..."))
        from apps.notifications.services.outbox_processor import OutboxProcessorService

        OutboxProcessorService().process_batch(limit=1000)

        # Phase 5: Guarantee Claims
        claims_seeder = BillingClaimsSeeder(password=password)
        claims_seeder.seed_all()

        self.stdout.write(
            self.style.SUCCESS(f"\nAll demo data has been successfully seeded!")
        )
        self.stdout.write(self.style.WARNING(f"Demo credentials password: {password}"))
