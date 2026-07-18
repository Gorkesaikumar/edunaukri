"""Seed realistic recent platform activity for the "Live Hiring Activity" feed.

Creates a spread of events across the last few hours (both domains) so the
public feed and the "activities today" counter look alive in demo/staging.

    python manage.py seed_activity            # top up to a healthy volume
    python manage.py seed_activity --fresh    # wipe existing, then seed
"""

import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.constants.enums import ActivityDomain, ActivityType
from apps.common.models import PlatformActivity

# (org_name, domain, activity_type, headline)
SEED = [
    (
        "Infosys",
        ActivityDomain.IT,
        ActivityType.JOB_POSTED,
        "posted Senior Java Developer",
    ),
    (
        "IIT Hyderabad",
        ActivityDomain.FACULTY,
        ActivityType.CANDIDATE_HIRED,
        "hired Associate Professor",
    ),
    (
        "Microsoft",
        ActivityDomain.IT,
        ActivityType.SHORTLISTED,
        "shortlisted 8 candidates",
    ),
    (
        "TCS",
        ActivityDomain.IT,
        ActivityType.JOB_POSTED,
        "opened 25 Software Engineer positions",
    ),
    (
        "Delhi Public School",
        ActivityDomain.FACULTY,
        ActivityType.CANDIDATE_HIRED,
        "hired PGT Mathematics Teacher",
    ),
    (
        "Google",
        ActivityDomain.IT,
        ActivityType.INTERVIEW_SCHEDULED,
        "scheduled interviews",
    ),
    (
        "Amazon",
        ActivityDomain.IT,
        ActivityType.OFFER_RELEASED,
        "released offer for Data Scientist",
    ),
    (
        "BITS Pilani",
        ActivityDomain.FACULTY,
        ActivityType.FACULTY_POSTED,
        "posted Assistant Professor - CSE",
    ),
    (
        "Wipro",
        ActivityDomain.IT,
        ActivityType.CANDIDATE_APPLIED,
        "received 42 applications",
    ),
    (
        "Amity University",
        ActivityDomain.FACULTY,
        ActivityType.UNIVERSITY_JOINED,
        "joined EduNaukri",
    ),
    (
        "Flipkart",
        ActivityDomain.IT,
        ActivityType.RECRUITER_VERIFIED,
        "was verified as a recruiter",
    ),
    (
        "Anna University",
        ActivityDomain.FACULTY,
        ActivityType.FACULTY_POSTED,
        "posted Professor of Physics",
    ),
    ("Zoho", ActivityDomain.IT, ActivityType.JOB_POSTED, "posted Full Stack Developer"),
    (
        "Christ University",
        ActivityDomain.FACULTY,
        ActivityType.SHORTLISTED,
        "shortlisted 5 lecturers",
    ),
    (
        "Swiggy",
        ActivityDomain.IT,
        ActivityType.CANDIDATE_HIRED,
        "hired Product Manager",
    ),
    (
        "VIT Vellore",
        ActivityDomain.FACULTY,
        ActivityType.INTERVIEW_SCHEDULED,
        "scheduled 12 interviews",
    ),
    ("Accenture", ActivityDomain.IT, ActivityType.COMPANY_JOINED, "joined EduNaukri"),
    (
        "Kendriya Vidyalaya",
        ActivityDomain.FACULTY,
        ActivityType.JOB_POSTED,
        "posted TGT Science Teacher",
    ),
    ("HCLTech", ActivityDomain.IT, ActivityType.OFFER_RELEASED, "released 3 offers"),
    (
        "SRM University",
        ActivityDomain.FACULTY,
        ActivityType.CANDIDATE_APPLIED,
        "received 28 applications",
    ),
    (
        "Cognizant",
        ActivityDomain.IT,
        ActivityType.SHORTLISTED,
        "shortlisted 15 candidates",
    ),
    (
        "Manipal Academy",
        ActivityDomain.FACULTY,
        ActivityType.RECRUITER_VERIFIED,
        "was verified as a recruiter",
    ),
    ("Paytm", ActivityDomain.IT, ActivityType.JOB_POSTED, "posted DevOps Engineer"),
    (
        "Ryan International",
        ActivityDomain.FACULTY,
        ActivityType.CANDIDATE_HIRED,
        "hired PRT English Teacher",
    ),
]


class Command(BaseCommand):
    help = "Seed recent platform activity for the Live Hiring Activity feed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing activity before seeding.",
        )

    def handle(self, *args, **options):
        if options["fresh"]:
            PlatformActivity.all_objects.all().delete()

        now = timezone.now()
        created = 0
        # Spread events across the last ~6 hours, newest first.
        minute = 1
        for org_name, domain, activity_type, headline in SEED:
            obj = PlatformActivity.objects.create(
                org_name=org_name,
                domain=domain,
                activity_type=activity_type,
                headline=headline,
                is_active=True,
            )
            # created_at has auto_now_add; override for a realistic spread.
            minute += random.randint(3, 22)
            PlatformActivity.objects.filter(pk=obj.pk).update(
                created_at=now - timezone.timedelta(minutes=minute)
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Platform activity seeded: {created} events.")
        )
