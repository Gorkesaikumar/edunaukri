"""Seed demo data for local development and integration testing."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import AdminUser, CollegeUser, ITUser, ProfessorUser
from apps.academic_recruitment.services.profile_service import ProfessorProfileService
from apps.billing.constants.enums import FeeType
from apps.billing.models import FeeSchedule
from apps.billing.services.placement_fee_service import FeeScheduleService
from apps.colleges.services.college_service import CollegeService
from apps.companies.services.company_service import CompanyService, JobPostingService
from apps.core.constants.enums import DomainType
from apps.it_recruitment.services.profile_service import ProfileService


class Command(BaseCommand):
    help = "Seed demo users, fee schedules, and sample domain records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="DemoPassword123!@#",
            help="Password for all demo users",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        created = []

        if not AdminUser.objects.filter(email="admin@demo.edunaukri").exists():
            AdminUser.objects.create_superuser("admin@demo.edunaukri", password)
            created.append("admin@demo.edunaukri")

        seeker, seeker_new = self._get_or_create_user(
            ITUser, "seeker@demo.edunaukri", password
        )
        if seeker_new:
            created.append("seeker@demo.edunaukri")

        recruiter, recruiter_new = self._get_or_create_user(
            ITUser, "recruiter@demo.edunaukri", password
        )
        if recruiter_new:
            created.append("recruiter@demo.edunaukri")

        professor, prof_new = self._get_or_create_user(
            ProfessorUser, "professor@demo.edunaukri", password
        )
        if prof_new:
            created.append("professor@demo.edunaukri")

        college_user, college_new = self._get_or_create_user(
            CollegeUser, "college@demo.edunaukri", password
        )
        if college_new:
            created.append("college@demo.edunaukri")

        if not hasattr(seeker, "job_seeker_profile"):
            ProfileService().create_job_seeker_profile(
                user=seeker,
                data={
                    "first_name": "Demo",
                    "last_name": "Seeker",
                    "headline": "Software Engineer",
                },
            )
            created.append("IT job seeker profile")

        if not hasattr(recruiter, "recruiter_profile"):
            recruiter_profile = ProfileService().create_recruiter_profile(
                user=recruiter,
                data={
                    "first_name": "Demo",
                    "last_name": "Recruiter",
                    "designation": "HR Manager",
                },
            )
        else:
            recruiter_profile = recruiter.recruiter_profile

        if not hasattr(professor, "professor_profile"):
            ProfessorProfileService().create_profile(
                user=professor,
                data={
                    "first_name": "Demo",
                    "last_name": "Professor",
                    "specialization": "Computer Science",
                },
            )
            created.append("Professor profile")

        if not recruiter_profile.company_memberships.exists():
            company = CompanyService().create_company(
                recruiter=recruiter_profile,
                data={"name": "Demo Tech Pvt Ltd", "industry": "IT Services"},
            )

            job = JobPostingService().create_draft(
                company=company,
                recruiter=recruiter_profile,
                data={
                    "title": "Senior Python Developer",
                    "description": "Build scalable APIs with Django.",
                },
            )
            JobPostingService().publish(job, recruiter=recruiter_profile)
            created.append(f"Company '{company.name}' + published job")

        if not college_user.college_memberships.exists():
            college = CollegeService().create_college(
                college_user=college_user,
                data={
                    "name": "Demo Engineering College",
                    "city": "Hyderabad",
                    "state": "Telangana",
                },
            )

            from apps.faculty.services.vacancy_service import VacancyPostingService

            vacancy = VacancyPostingService().create_draft(
                college=college,
                college_user=college_user,
                data={
                    "title": "Assistant Professor — CS",
                    "description": "Teach UG/PG computer science courses.",
                },
            )
            VacancyPostingService().publish(vacancy, college_user=college_user)
            created.append(f"College '{college.name}' + published vacancy")

        fee_service = FeeScheduleService()
        if not FeeSchedule.objects.filter(
            domain=DomainType.IT, is_deleted=False
        ).exists():
            fee_service.create_schedule(
                data={
                    "domain": DomainType.IT,
                    "name": "Demo IT Placement Fee",
                    "fee_type": FeeType.FIXED,
                    "fixed_amount": Decimal("50000"),
                }
            )
            created.append("IT fee schedule")

        if not FeeSchedule.objects.filter(
            domain=DomainType.FACULTY, is_deleted=False
        ).exists():
            fee_service.create_schedule(
                data={
                    "domain": DomainType.FACULTY,
                    "name": "Demo Faculty Placement Fee",
                    "fee_type": FeeType.FIXED,
                    "fixed_amount": Decimal("75000"),
                }
            )
            created.append("Faculty fee schedule")

        if created:
            self.stdout.write(self.style.SUCCESS("Created:"))
            for item in created:
                self.stdout.write(f"  - {item}")
        else:
            self.stdout.write("Demo data already present — nothing to seed.")

        self.stdout.write(self.style.WARNING(f"\nDemo password: {password}"))

    def _get_or_create_user(self, model, email, password):
        user = model.objects.filter(email=email).first()
        if user:
            return user, False
        user = model.objects.create_user(email, password)
        return user, True
