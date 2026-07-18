"""Seed a set of realistic, verified placement testimonials for the landing page.

Idempotent: re-running updates the existing rows (matched by author_name)
instead of creating duplicates. Intended for demo / staging environments.

    python manage.py seed_testimonials
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.constants.enums import (
    TestimonialDomain,
    TestimonialVisibility,
)
from apps.common.models import Testimonial

SEED = [
    {
        "author_name": "Ananya Sharma",
        "designation": "Senior Software Engineer",
        "organization_name": "Google",
        "domain": TestimonialDomain.IT,
        "rating": 5,
        "quote": "EduNaukri connected me with roles that actually matched my stack. Within three weeks I had multiple offers and joined my dream team.",
        "days_to_hire": 18,
        "salary_increase_pct": 45,
        "joined_dream_company": True,
    },
    {
        "author_name": "Dr. Rajeev Menon",
        "designation": "Associate Professor",
        "organization_name": "IIT Hyderabad",
        "domain": TestimonialDomain.FACULTY,
        "rating": 5,
        "quote": "The faculty recruitment process was transparent and dignified. I found a research-focused institution that values my work.",
        "days_to_hire": 26,
        "salary_increase_pct": 30,
        "joined_dream_company": True,
    },
    {
        "author_name": "Priya Nair",
        "designation": "Principal",
        "organization_name": "Delhi Public School",
        "domain": TestimonialDomain.FACULTY,
        "rating": 5,
        "quote": "As a school leader, I appreciated how verified and serious every opportunity was. The placement felt effortless and professional.",
        "days_to_hire": 21,
        "salary_increase_pct": 25,
        "joined_dream_company": False,
    },
    {
        "author_name": "Arjun Verma",
        "designation": "Engineering Manager",
        "organization_name": "Microsoft",
        "domain": TestimonialDomain.IT,
        "rating": 5,
        "quote": "The quality of openings on EduNaukri is unmatched. I moved into a leadership role with a significant compensation jump.",
        "days_to_hire": 24,
        "salary_increase_pct": 52,
        "joined_dream_company": True,
    },
    {
        "author_name": "Sneha Iyer",
        "designation": "Data Scientist",
        "organization_name": "Amazon",
        "domain": TestimonialDomain.IT,
        "rating": 5,
        "quote": "From application to offer, everything was tracked in real time. Recruiters were responsive and the process was seamless.",
        "days_to_hire": 15,
        "salary_increase_pct": 38,
        "joined_dream_company": False,
    },
    {
        "author_name": "Dr. Kavita Rao",
        "designation": "Assistant Professor",
        "organization_name": "BITS Pilani",
        "domain": TestimonialDomain.FACULTY,
        "rating": 5,
        "quote": "I secured a tenure-track position that aligns perfectly with my research interests. Truly a platform built for educators.",
        "days_to_hire": 29,
        "salary_increase_pct": 22,
        "joined_dream_company": True,
    },
    {
        "author_name": "Mohit Gupta",
        "designation": "DevOps Engineer",
        "organization_name": "Flipkart",
        "domain": TestimonialDomain.IT,
        "rating": 4,
        "quote": "Great experience overall. The verified employer badges gave me confidence that every opportunity was genuine.",
        "days_to_hire": 20,
        "salary_increase_pct": 33,
        "joined_dream_company": False,
    },
    {
        "author_name": "Fatima Khan",
        "designation": "Head of Department",
        "organization_name": "Amity University",
        "domain": TestimonialDomain.FACULTY,
        "rating": 5,
        "quote": "The platform understood the nuances of academic hiring. I was matched with an institution that shares my vision for education.",
        "days_to_hire": 31,
        "salary_increase_pct": 28,
        "joined_dream_company": True,
    },
    {
        "author_name": "Rohan Desai",
        "designation": "Full Stack Developer",
        "organization_name": "Zoho",
        "domain": TestimonialDomain.IT,
        "rating": 5,
        "quote": "One profile, one-click applications, and constant updates. EduNaukri made my job switch stress-free and fast.",
        "days_to_hire": 12,
        "salary_increase_pct": 41,
        "joined_dream_company": False,
    },
    {
        "author_name": "Dr. Meera Krishnan",
        "designation": "Professor of Physics",
        "organization_name": "Anna University",
        "domain": TestimonialDomain.FACULTY,
        "rating": 5,
        "quote": "A respectful, well-structured hiring journey. I felt valued at every stage and landed a role I am proud of.",
        "days_to_hire": 27,
        "salary_increase_pct": 24,
        "joined_dream_company": True,
    },
    {
        "author_name": "Vikram Singh",
        "designation": "Product Manager",
        "organization_name": "Swiggy",
        "domain": TestimonialDomain.IT,
        "rating": 5,
        "quote": "The curated matches saved me weeks of searching. I connected directly with decision-makers and closed an offer quickly.",
        "days_to_hire": 17,
        "salary_increase_pct": 48,
        "joined_dream_company": True,
    },
    {
        "author_name": "Aisha Patel",
        "designation": "Lecturer in Mathematics",
        "organization_name": "Christ University",
        "domain": TestimonialDomain.FACULTY,
        "rating": 4,
        "quote": "Verified institutions and clear communication made all the difference. Highly recommended for fellow educators.",
        "days_to_hire": 23,
        "salary_increase_pct": 26,
        "joined_dream_company": False,
    },
]


class Command(BaseCommand):
    help = "Seed verified placement testimonials for the landing page carousel."

    def handle(self, *args, **options):
        now = timezone.now()
        created, updated = 0, 0
        for offset, data in enumerate(SEED):
            defaults = {
                **data,
                "is_verified": True,
                "is_active": True,
                "visibility": TestimonialVisibility.PUBLIC,
                # Stagger published_at so newest-first ordering is deterministic.
                "published_at": now - timezone.timedelta(days=offset),
            }
            _, was_created = Testimonial.objects.update_or_create(
                author_name=data["author_name"], defaults=defaults
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Testimonials seeded: {created} created, {updated} updated."
            )
        )
