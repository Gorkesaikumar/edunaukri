import logging
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clears and recreates fresh demo data by chaining clear_demo_data and seed_demo_data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force deletion and recreation without prompt",
        )
        parser.add_argument(
            "--password",
            default="DemoPassword123!@#",
            help="Password for all demo users",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Reseed Process..."))

        # Call clear
        call_command("clear_demo_data", force=options["force"])

        # Call seed
        self.stdout.write(self.style.SUCCESS("Data cleared. Initiating seeding..."))
        call_command(
            "seed_demo_data", password=options["password"], force=options["force"]
        )

        self.stdout.write(self.style.SUCCESS("Reseed complete!"))
