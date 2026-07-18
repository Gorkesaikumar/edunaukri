from django.core.management.base import BaseCommand

from apps.notifications.services.outbox_processor import OutboxProcessorService


class Command(BaseCommand):
    help = "Process pending outbox events and dispatch in-app notifications."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=50)

    def handle(self, *args, **options):
        count = OutboxProcessorService().process_batch(limit=options["batch_size"])
        self.stdout.write(self.style.SUCCESS(f"Processed {count} outbox event(s)."))
