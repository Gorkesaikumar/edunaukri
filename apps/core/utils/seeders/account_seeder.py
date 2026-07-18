from .base_seeder import BaseSeeder
from apps.accounts.models import ITUser, ProfessorUser, CollegeUser
from apps.it_recruitment.services.profile_service import ProfileService
from apps.academic_recruitment.services.profile_service import ProfessorProfileService
from apps.companies.services.company_service import CompanyService
from apps.colleges.services.college_service import CollegeService


class AccountSeeder(BaseSeeder):
    COMPANIES = [
        "Nextora Technologies",
        "TechNova Pvt Ltd",
        "CloudSpark Solutions",
        "PixelStack Systems",
        "DevFusion Labs",
        "SoftBridge Technologies",
        "Apex Software",
        "ByteWorks",
        "CodeMatrix",
        "FutureTech Systems",
    ]

    INSTITUTIONS = [
        "Ram Suns Public School",
        "Demo Engineering College",
        "Oxford Junior College",
        "Green Valley School",
        "Sri Chaitanya College",
        "National Degree College",
        "Bright Future School",
        "Sunrise International School",
        "Global University",
        "Wisdom Public School",
    ]

    def seed_recruiters(self):
        self.log("Seeding IT Recruiters...")
        for i, company_name in enumerate(self.COMPANIES):
            email = f"recruiter{i}@demo.edunaukri"
            user = ITUser.objects.create_user(email, self.password)

            # Create recruiter profile
            recruiter_profile = ProfileService().create_recruiter_profile(
                user=user,
                data={
                    "first_name": self.faker.first_name(),
                    "last_name": self.faker.last_name(),
                    "designation": "HR Manager",
                    "mobile": f"+9198{self.faker.random_number(digits=8, fix_len=True)}",
                },
            )

            # Create company
            CompanyService().create_company(
                recruiter=recruiter_profile,
                data={
                    "name": company_name,
                    "industry": "IT Services",
                    "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
                    "address": self.faker.address(),
                },
            )

    def seed_colleges(self):
        self.log("Seeding Faculty Institutions (Colleges)...")
        for i, college_name in enumerate(self.INSTITUTIONS):
            email = f"college{i}@demo.edunaukri"
            user = CollegeUser.objects.create_user(email, self.password)

            CollegeService().create_college(
                college_user=user,
                data={
                    "name": college_name,
                    "city": self.faker.city(),
                    "state": self.faker.state(),
                    "address": self.faker.address(),
                    "website": f"https://www.{college_name.lower().replace(' ', '')}.edu",
                },
            )

    def seed_it_job_seekers(self, count=50):
        self.log(f"Seeding {count} IT Job Seekers...")
        experience_levels = [
            "Freshers",
            "1 Year",
            "2 Years",
            "3 Years",
            "5 Years",
            "Senior Developer",
        ]
        for i in range(count):
            email = f"seeker{i}@demo.edunaukri"
            user = ITUser.objects.create_user(email, self.password)

            ProfileService().create_job_seeker_profile(
                user=user,
                data={
                    "first_name": self.faker.first_name(),
                    "last_name": self.faker.last_name(),
                    "headline": f"{self.faker.random_element(experience_levels)} Software Engineer",
                    "mobile": f"+9198{self.faker.random_number(digits=8, fix_len=True)}",
                    "current_location": self.faker.city(),
                },
            )

    def seed_faculty_job_seekers(self, count=50):
        self.log(f"Seeding {count} Faculty Job Seekers...")
        specializations = [
            "Computer Science",
            "Physics",
            "Mathematics",
            "English",
            "Chemistry",
        ]
        for i in range(count):
            email = f"professor{i}@demo.edunaukri"
            user = ProfessorUser.objects.create_user(email, self.password)

            ProfessorProfileService().create_profile(
                user=user,
                data={
                    "first_name": self.faker.first_name(),
                    "last_name": self.faker.last_name(),
                    "specialization": self.faker.random_element(specializations),
                    "mobile": f"+9198{self.faker.random_number(digits=8, fix_len=True)}",
                    "location": self.faker.city(),
                },
            )

    def seed_all(self):
        self.seed_recruiters()
        self.seed_colleges()
        self.seed_it_job_seekers()
        self.seed_faculty_job_seekers()
