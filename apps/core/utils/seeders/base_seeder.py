import random
from faker import Faker
from django.utils import timezone
from datetime import timedelta

fake = Faker("en_IN")


class BaseSeeder:
    def __init__(self, password="DemoPassword123!@#"):
        self.password = password
        self.faker = fake

    def _get_random_past_date(self, max_days_ago=90):
        return timezone.now() - timedelta(
            days=random.randint(1, max_days_ago), hours=random.randint(1, 24)
        )

    def _get_random_future_date(self, max_days_ahead=30):
        return timezone.now() + timedelta(
            days=random.randint(1, max_days_ahead), hours=random.randint(1, 24)
        )

    def log(self, message):
        print(f"[*] {message}")
