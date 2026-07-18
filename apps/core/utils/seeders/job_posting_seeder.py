from decimal import Decimal
from .base_seeder import BaseSeeder
from apps.companies.models import Company
from apps.colleges.models import College
from apps.companies.services.company_service import JobPostingService
from apps.faculty.services.vacancy_service import VacancyPostingService


class JobPostingSeeder(BaseSeeder):
    IT_JOB_TITLES = [
        "Python Developer",
        "Django Developer",
        "React Developer",
        "Full Stack Developer",
        "Flutter Developer",
        "Java Developer",
        "DevOps Engineer",
        "Data Analyst",
        "UI UX Designer",
        "AI Engineer",
    ]

    FACULTY_JOB_TITLES = [
        "Assistant Professor",
        "Associate Professor",
        "Principal",
        "Lecturer",
        "Physics Faculty",
        "Chemistry Faculty",
        "English Faculty",
        "Mathematics Faculty",
        "Computer Science Faculty",
        "Librarian",
    ]

    def seed_it_jobs(self, count=50):
        self.log(f"Seeding {count} IT Job Postings...")
        companies = list(Company.objects.all())
        if not companies:
            return

        for _ in range(count):
            company = self.faker.random_element(companies)
            recruiter = company.members.first().recruiter

            try:
                job = JobPostingService().create_draft(
                    company=company,
                    recruiter=recruiter,
                    data={
                        "title": f"{self.faker.random_element(self.IT_JOB_TITLES)} - {self.faker.unique.random_number(digits=4)}",
                        "description": self.faker.paragraph(nb_sentences=5),
                        "min_salary": Decimal(self.faker.random_int(300000, 500000)),
                        "max_salary": Decimal(self.faker.random_int(600000, 1500000)),
                        "experience_years": self.faker.random_int(0, 8),
                        "location": self.faker.city(),
                        "vacancy_count": self.faker.random_int(1, 10),
                    },
                )
                JobPostingService().publish(job, recruiter=recruiter)
            except Exception as e:
                self.log(f"Skipped duplicate job: {e}")

    def seed_faculty_vacancies(self, count=50):
        self.log(f"Seeding {count} Faculty Vacancies...")
        colleges = list(College.objects.all())
        if not colleges:
            return

        for _ in range(count):
            college = self.faker.random_element(colleges)
            college_user = college.members.first().college_user

            try:
                vacancy = VacancyPostingService().create_draft(
                    college=college,
                    college_user=college_user,
                    data={
                        "title": f"{self.faker.random_element(self.FACULTY_JOB_TITLES)} - {self.faker.unique.random_number(digits=4)}",
                        "description": self.faker.paragraph(nb_sentences=5),
                        "min_salary": Decimal(self.faker.random_int(300000, 500000)),
                        "max_salary": Decimal(self.faker.random_int(600000, 1500000)),
                        "experience_years": self.faker.random_int(0, 15),
                        "location": self.faker.city(),
                    },
                )
                VacancyPostingService().publish(vacancy, college_user=college_user)
            except Exception as e:
                self.log(f"Skipped duplicate vacancy: {e}")

    def seed_all(self):
        self.seed_it_jobs()
        self.seed_faculty_vacancies()
