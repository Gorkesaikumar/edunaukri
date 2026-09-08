import os
import sys
import random
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from unittest.mock import patch

# Initialize Django if executed standalone
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    import django
    django.setup()

from apps.accounts.models import ITUser
from apps.accounts.models.it_user_role import ITUserRole
from apps.accounts.constants.enums import ITUserRoleType
from apps.billing.models import FeeSchedule, PlacementFee
from apps.billing.constants.enums import FeeType
from apps.companies.models import Company, CompanyMember
from apps.companies.constants.enums import CompanyMemberRole, CompanySize
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.documents.models import StoredFile
from apps.documents.constants.enums import StorageFileType, StorageBackendType
from apps.guarantee_claims.models import GuaranteeClaim, GuaranteeClaimHistory, PlacementGuarantee
from apps.guarantee_claims.constants.enums import ClaimStatus, ClaimType, ExitReason, GuaranteeStatus
from apps.invoices.models import Invoice, InvoiceLineItem
from apps.it_recruitment.models import (
    JobSeekerProfile,
    RecruiterProfile,
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProject,
    JobSeekerCertification,
)
from apps.it_recruitment.constants.education_enums import (
    EducationLevel,
    EducationBoard,
    IntermediateStream,
    EducationScoreType,
)
from apps.jobs.models import (
    JobPosting,
    JobPostingSkill,
    JobLocation,
    JobSeekerSkill,
    Skill,
    SavedJob,
)
from apps.jobs.constants.enums import EmploymentType, JobStatus, WorkMode, SalaryVisibility
from apps.applications.models import (
    JobApplication,
    JobApplicationStatusHistory,
    JobApplicationTimelineEvent,
    JobApplicationInterview,
    PlacementDetails,
    InterviewEvaluation,
)
from apps.applications.constants.enums import JobApplicationStatus, ApplicationSource, TimelineEventType
from apps.applications.constants.interview_enums import InterviewRoundType, InterviewMode, InterviewStatus

DEMO_PASSWORD = "Demo@12345"

# Telugu-named IT candidates dataset
JOB_SEEKERS_DATA = [
    {
        "email": "it.seeker01.saikiran@example.com",
        "first_name": "Sai Kiran",
        "last_name": "Reddy",
        "phone": "+919848012345",
        "headline": "Python Django Full Stack Engineer",
        "summary": "Experienced Python & Django developer with 4 years building scalable web apps and REST APIs.",
        "experience_years": 4,
        "city": "Hyderabad",
        "state": "Telangana",
        "current_location": "Hyderabad",
        "preferred_location": "Hyderabad, Remote",
        "current_company": "TechWave Solutions",
        "current_salary": Decimal("850000.00"),
        "expected_salary": Decimal("1200000.00"),
        "notice_period_days": 30,
        "skills": ["Python", "Django", "PostgreSQL", "REST APIs", "Git", "Docker"],
        "primary_role": "python",
    },
    {
        "email": "it.seeker02.anusha@example.com",
        "first_name": "Anusha",
        "last_name": "Goud",
        "phone": "+919848012346",
        "headline": "React Frontend Developer",
        "summary": "UI/UX enthusiast with 3 years of experience in React, TypeScript, and modern CSS systems.",
        "experience_years": 3,
        "city": "Secunderabad",
        "state": "Telangana",
        "current_location": "Secunderabad",
        "preferred_location": "Hyderabad, Bengaluru",
        "current_company": "PixelCraft Studio",
        "current_salary": Decimal("700000.00"),
        "expected_salary": Decimal("1000000.00"),
        "notice_period_days": 15,
        "skills": ["React", "JavaScript", "TypeScript", "HTML5/CSS3", "Git"],
        "primary_role": "react",
    },
    {
        "email": "it.seeker03.venkatesh@example.com",
        "first_name": "Venkatesh",
        "last_name": "Yadav",
        "phone": "+919848012347",
        "headline": "Junior Backend Developer - Python/FastAPI",
        "summary": "Enthusiastic Junior Developer skilled in Python, FastAPI, SQL, and backend architecture.",
        "experience_years": 1,
        "city": "Warangal",
        "state": "Telangana",
        "current_location": "Warangal",
        "preferred_location": "Hyderabad",
        "current_company": "InnoSoft Systems",
        "current_salary": Decimal("400000.00"),
        "expected_salary": Decimal("600000.00"),
        "notice_period_days": 30,
        "skills": ["Python", "FastAPI", "SQL", "Git"],
        "primary_role": "backend",
    },
    {
        "email": "it.seeker04.nikhila@example.com",
        "first_name": "Nikhila",
        "last_name": "Reddy",
        "phone": "+919848012348",
        "headline": "Data Analyst & Business Intelligence Specialist",
        "summary": "Data Analyst with 2 years of experience turning raw dataset into actionable business insights.",
        "experience_years": 2,
        "city": "Nizamabad",
        "state": "Telangana",
        "current_location": "Nizamabad",
        "preferred_location": "Hyderabad, Remote",
        "current_company": "Analytics Insights",
        "current_salary": Decimal("550000.00"),
        "expected_salary": Decimal("800000.00"),
        "notice_period_days": 30,
        "skills": ["Python", "SQL", "Power BI", "Pandas", "NumPy", "Data Analysis"],
        "primary_role": "data",
    },
    {
        "email": "it.seeker05.arjun@example.com",
        "first_name": "Arjun",
        "last_name": "Naidu",
        "phone": "+919848012349",
        "headline": "DevOps & Cloud Infrastructure Engineer",
        "summary": "DevOps Engineer with 5 years experience managing AWS cloud infra, CI/CD pipelines, and Kubernetes.",
        "experience_years": 5,
        "city": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "current_location": "Visakhapatnam",
        "preferred_location": "Hyderabad, Remote",
        "current_company": "CloudSphere Inc",
        "current_salary": Decimal("1300000.00"),
        "expected_salary": Decimal("1800000.00"),
        "notice_period_days": 45,
        "skills": ["AWS", "Docker", "Kubernetes", "Linux", "Git", "Python"],
        "primary_role": "devops",
    },
    {
        "email": "it.seeker06.swathi@example.com",
        "first_name": "Swathi",
        "last_name": "Rao",
        "phone": "+919848012350",
        "headline": "Java Spring Boot Senior Engineer",
        "summary": "Senior Java Developer with 5 years experience in enterprise Spring Boot microservices.",
        "experience_years": 5,
        "city": "Vijayawada",
        "state": "Andhra Pradesh",
        "current_location": "Vijayawada",
        "preferred_location": "Hyderabad, Bengaluru",
        "current_company": "Enterprise Java Systems",
        "current_salary": Decimal("1200000.00"),
        "expected_salary": Decimal("1600000.00"),
        "notice_period_days": 60,
        "skills": ["Java", "Spring Boot", "SQL", "PostgreSQL", "REST APIs", "Git"],
        "primary_role": "java",
    },
    {
        "email": "it.seeker07.karthik@example.com",
        "first_name": "Karthik",
        "last_name": "Varma",
        "phone": "+919848012351",
        "headline": "Machine Learning Engineer",
        "summary": "ML Engineer with 3 years experience building predictive models and NLP applications.",
        "experience_years": 3,
        "city": "Karimnagar",
        "state": "Telangana",
        "current_location": "Karimnagar",
        "preferred_location": "Hyderabad, Remote",
        "current_company": "Cognitive AI Labs",
        "current_salary": Decimal("900000.00"),
        "expected_salary": Decimal("1400000.00"),
        "notice_period_days": 30,
        "skills": ["Python", "Machine Learning", "Pandas", "NumPy", "Scikit-learn", "FastAPI"],
        "primary_role": "ml",
    },
    {
        "email": "it.seeker08.harika@example.com",
        "first_name": "Harika",
        "last_name": "Reddy",
        "phone": "+919848012352",
        "headline": "QA Automation Engineer",
        "summary": "QA Engineer with 3 years experience in Python Selenium, pytest, and automated regression testing.",
        "experience_years": 3,
        "city": "Khammam",
        "state": "Telangana",
        "current_location": "Khammam",
        "preferred_location": "Hyderabad",
        "current_company": "QualityFirst Tech",
        "current_salary": Decimal("650000.00"),
        "expected_salary": Decimal("950000.00"),
        "notice_period_days": 30,
        "skills": ["Python", "REST APIs", "SQL", "Git", "Linux"],
        "primary_role": "qa",
    },
    {
        "email": "it.seeker09.rahul@example.com",
        "first_name": "Rahul",
        "last_name": "Goud",
        "phone": "+919848012353",
        "headline": "Software Support Engineer",
        "summary": "Support Engineer with 2 years experience troubleshooting Linux web servers and database queries.",
        "experience_years": 2,
        "city": "Gachibowli",
        "state": "Telangana",
        "current_location": "Gachibowli",
        "preferred_location": "Hyderabad",
        "current_company": "AppSupport Corp",
        "current_salary": Decimal("480000.00"),
        "expected_salary": Decimal("700000.00"),
        "notice_period_days": 15,
        "skills": ["Linux", "SQL", "REST APIs", "Git"],
        "primary_role": "support",
    },
    {
        "email": "it.seeker10.divyasri@example.com",
        "first_name": "Divya Sri",
        "last_name": "Kambhampati",
        "phone": "+919848012354",
        "headline": "Full Stack Engineer (Node.js & React)",
        "summary": "Versatile Full Stack engineer with 3 years experience across React frontend and Node.js backend.",
        "experience_years": 3,
        "city": "Madhapur",
        "state": "Telangana",
        "current_location": "Madhapur",
        "preferred_location": "Hyderabad, Remote",
        "current_company": "NodeWorks Technologies",
        "current_salary": Decimal("800000.00"),
        "expected_salary": Decimal("1150000.00"),
        "notice_period_days": 30,
        "skills": ["Node.js", "React", "JavaScript", "TypeScript", "MongoDB", "REST APIs"],
        "primary_role": "fullstack",
    },
]

# Telugu-named Recruiters and IT Companies dataset
RECRUITERS_COMPANIES_DATA = [
    {
        "email": "it.recruiter01.sravani@example.com",
        "first_name": "Sravani",
        "last_name": "Reddy",
        "phone": "+919849011101",
        "designation": "Lead Technical Recruiter",
        "company_name": "[DEMO-IT] VedaSoft Technologies",
        "website": "https://www.vedasoft.demo",
        "industry": "IT Services & Consulting",
        "city": "Hyderabad",
    },
    {
        "email": "it.recruiter02.saiteja@example.com",
        "first_name": "Sai Teja",
        "last_name": "Koppula",
        "phone": "+919849011102",
        "designation": "Talent Acquisition Manager",
        "company_name": "[DEMO-IT] TechSutra Labs",
        "website": "https://www.techsutralabs.demo",
        "industry": "Software Product Development",
        "city": "Hyderabad",
    },
    {
        "email": "it.recruiter03.manoj@example.com",
        "first_name": "Manoj Kumar",
        "last_name": "Vangala",
        "phone": "+919849011103",
        "designation": "Senior IT Recruiter",
        "company_name": "[DEMO-IT] NexByte Systems",
        "website": "https://www.nexbyte.demo",
        "industry": "Cloud & Infrastructure Solutions",
        "city": "Gachibowli",
    },
    {
        "email": "it.recruiter04.lakshmi@example.com",
        "first_name": "Lakshmi",
        "last_name": "Prasanna",
        "phone": "+919849011104",
        "designation": "HR Business Partner",
        "company_name": "[DEMO-IT] CloudVista Technologies",
        "website": "https://www.cloudvista.demo",
        "industry": "Cloud Managed Services",
        "city": "Madhapur",
    },
    {
        "email": "it.recruiter05.rohit@example.com",
        "first_name": "Rohit",
        "last_name": "Varma",
        "phone": "+919849011105",
        "designation": "Talent Acquisition Specialist",
        "company_name": "[DEMO-IT] ManaTech Solutions",
        "website": "https://www.manatech.demo",
        "industry": "Enterprise Software",
        "city": "Hyderabad",
    },
    {
        "email": "it.recruiter06.keerthana@example.com",
        "first_name": "Keerthana",
        "last_name": "Goud",
        "phone": "+919849011106",
        "designation": "Recruitment Lead",
        "company_name": "[DEMO-IT] BlueOrbit Software",
        "website": "https://www.blueorbit.demo",
        "industry": "SaaS & Web Applications",
        "city": "Secunderabad",
    },
    {
        "email": "it.recruiter07.praveen@example.com",
        "first_name": "Praveen",
        "last_name": "Reddy",
        "phone": "+919849011107",
        "designation": "HR Manager",
        "company_name": "[DEMO-IT] PixelForge Technologies",
        "website": "https://www.pixelforge.demo",
        "industry": "Digital Transformation & Design",
        "city": "Hyderabad",
    },
    {
        "email": "it.recruiter08.deepika@example.com",
        "first_name": "Deepika",
        "last_name": "Rao",
        "phone": "+919849011108",
        "designation": "Senior Staffing Consultant",
        "company_name": "[DEMO-IT] InnoStack Labs",
        "website": "https://www.innostack.demo",
        "industry": "AI & Data Solutions",
        "city": "Gachibowli",
    },
    {
        "email": "it.recruiter09.naveen@example.com",
        "first_name": "Naveen",
        "last_name": "Kumar",
        "phone": "+919849011109",
        "designation": "Technical Sourcing Lead",
        "company_name": "[DEMO-IT] CodeVeda Systems",
        "website": "https://www.codeveda.demo",
        "industry": "Custom Software Engineering",
        "city": "Madhapur",
    },
    {
        "email": "it.recruiter10.sirisha@example.com",
        "first_name": "Sirisha",
        "last_name": "Naidu",
        "phone": "+919849011110",
        "designation": "Head of HR",
        "company_name": "[DEMO-IT] Arya Digital Labs",
        "website": "https://www.aryadigital.demo",
        "industry": "FinTech & Digital Payments",
        "city": "Hyderabad",
    },
]

# 10 IT Job Postings dataset
JOBS_DATA = [
    {
        "index": 0,
        "title": "Python Django Developer",
        "role_key": "python",
        "description": "We are seeking a skilled Python Django Developer to build robust backend API services, handle database optimization, and collaborate with cross-functional teams.",
        "requirements": "Strong experience with Python 3.x, Django framework, PostgreSQL, RESTful APIs, Git, and Docker containerization.",
        "roles_responsibilities": "Design and implement API endpoints, write clean unit tests, optimize database queries, participate in code reviews.",
        "benefits": "Competitive CTC, Health Insurance, Flexible Hybrid Work, Performance Bonuses.",
        "education_requirement": "B.Tech/B.E. in Computer Science or related field",
        "experience_min": 2,
        "experience_max": 5,
        "salary_min": Decimal("800000.00"),
        "salary_max": Decimal("1300000.00"),
        "vacancies": 3,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.HYBRID,
        "city": "Hyderabad",
        "required_skills": ["Python", "Django", "PostgreSQL", "REST APIs"],
        "preferred_skills": ["Docker", "Git"],
        "days_ago_posted": 55,
    },
    {
        "index": 1,
        "title": "Junior Backend Developer",
        "role_key": "backend",
        "description": "Looking for an energetic Junior Backend Developer to assist in building cloud-native microservices using Python & FastAPI.",
        "requirements": "Hands-on experience with Python, FastAPI or Flask, SQL databases, and basic web architecture concepts.",
        "roles_responsibilities": "Develop backend logic, assist senior developers, debug production issues, maintain documentation.",
        "benefits": "Mentorship, Annual Learning Allowance, Health Cover.",
        "education_requirement": "B.Tech/B.Sc Computer Science",
        "experience_min": 0,
        "experience_max": 2,
        "salary_min": Decimal("400000.00"),
        "salary_max": Decimal("650000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.ONSITE,
        "city": "Hyderabad",
        "required_skills": ["Python", "FastAPI", "SQL"],
        "preferred_skills": ["Git", "PostgreSQL"],
        "days_ago_posted": 50,
    },
    {
        "index": 2,
        "title": "React Frontend Developer",
        "role_key": "react",
        "description": "Join our frontend engineering team to build sleek, reactive user interfaces for SaaS web platforms using React and TypeScript.",
        "requirements": "Proficiency in React.js, JavaScript (ES6+), TypeScript, HTML5, CSS3, state management (Redux/Context API), and REST API integration.",
        "roles_responsibilities": "Translate Figma designs into pixel-perfect React components, optimize frontend performance, implement responsive layouts.",
        "benefits": "Remote options, Mac Workstation, Wellness stipend.",
        "education_requirement": "B.E./B.Tech/MCA",
        "experience_min": 2,
        "experience_max": 4,
        "salary_min": Decimal("750000.00"),
        "salary_max": Decimal("1100000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.HYBRID,
        "city": "Hyderabad",
        "required_skills": ["React", "JavaScript", "TypeScript", "HTML5/CSS3"],
        "preferred_skills": ["Git", "REST APIs"],
        "days_ago_posted": 45,
    },
    {
        "index": 3,
        "title": "Full Stack Developer (Node.js & React)",
        "role_key": "fullstack",
        "description": "Seeking an end-to-end Full Stack Engineer capable of handling Node.js backend services and React frontend features.",
        "requirements": "Solid experience with Node.js, Express, React, MongoDB/PostgreSQL, TypeScript, and AWS cloud deployment.",
        "roles_responsibilities": "Architect full-stack modules, write scalable APIs, build dynamic frontend components, maintain CI/CD pipelines.",
        "benefits": "Flexible hours, Stock options, Health insurance.",
        "education_requirement": "B.Tech/M.Tech Computer Science",
        "experience_min": 3,
        "experience_max": 6,
        "salary_min": Decimal("900000.00"),
        "salary_max": Decimal("1400000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.HYBRID,
        "city": "Gachibowli",
        "required_skills": ["Node.js", "React", "JavaScript", "TypeScript"],
        "preferred_skills": ["MongoDB", "REST APIs", "AWS"],
        "days_ago_posted": 40,
    },
    {
        "index": 4,
        "title": "Java Spring Boot Senior Developer",
        "role_key": "java",
        "description": "Enterprise software division needs an experienced Java Spring Boot developer for microservices modernization.",
        "requirements": "Deep expertise in Core Java, Spring Boot, Hibernate, Microservices, PostgreSQL/Oracle, Kafka, and Docker.",
        "roles_responsibilities": "Develop enterprise microservices, ensure high availability, design DB schemas, conduct technical code reviews.",
        "benefits": "High growth CTC, Annual bonus, Insurance for family.",
        "education_requirement": "B.Tech / M.Tech / MCA",
        "experience_min": 4,
        "experience_max": 8,
        "salary_min": Decimal("1200000.00"),
        "salary_max": Decimal("1700000.00"),
        "vacancies": 4,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.ONSITE,
        "city": "Madhapur",
        "required_skills": ["Java", "Spring Boot", "SQL", "PostgreSQL"],
        "preferred_skills": ["REST APIs", "Docker", "Git"],
        "days_ago_posted": 38,
    },
    {
        "index": 5,
        "title": "Data Analyst",
        "role_key": "data",
        "description": "Looking for a Data Analyst to transform complex business data into clear dashboards and actionable operational reports.",
        "requirements": "Expertise in SQL, Python, Power BI/Tableau, Excel, and data visualization techniques.",
        "roles_responsibilities": "Write complex SQL queries, build interactive Power BI dashboards, analyze KPI metrics for management.",
        "benefits": "Learning credits, Hybrid work model, Quarterly bonuses.",
        "education_requirement": "Degree in Statistics, Mathematics, CS or Data Science",
        "experience_min": 1,
        "experience_max": 4,
        "salary_min": Decimal("600000.00"),
        "salary_max": Decimal("900000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.HYBRID,
        "city": "Hyderabad",
        "required_skills": ["SQL", "Power BI", "Python", "Data Analysis"],
        "preferred_skills": ["Pandas", "NumPy"],
        "days_ago_posted": 35,
    },
    {
        "index": 6,
        "title": "Machine Learning Engineer",
        "role_key": "ml",
        "description": "AI division seeks an ML Engineer to develop, train, and deploy predictive ML models and LLM wrappers into production.",
        "requirements": "Strong background in Python, Scikit-learn, TensorFlow/PyTorch, Pandas, NumPy, and REST API model serving.",
        "roles_responsibilities": "Train & evaluate ML models, clean training datasets, deploy inference APIs, optimize model latency.",
        "benefits": "AI Hardware budget, Conference sponsorship, Flexible hours.",
        "education_requirement": "B.Tech/M.Tech in CS/AI/DS",
        "experience_min": 2,
        "experience_max": 5,
        "salary_min": Decimal("1000000.00"),
        "salary_max": Decimal("1500000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.REMOTE,
        "city": "Remote",
        "required_skills": ["Python", "Machine Learning", "Pandas", "NumPy", "Scikit-learn"],
        "preferred_skills": ["FastAPI", "Git"],
        "days_ago_posted": 30,
    },
    {
        "index": 7,
        "title": "DevOps Engineer",
        "role_key": "devops",
        "description": "We need a DevOps Specialist to manage cloud infrastructure, automate deployment pipelines, and ensure 99.9% system uptime.",
        "requirements": "Hands-on experience with AWS, Terraform, Docker, Kubernetes, Linux admin, Bash/Python scripting, and GitHub Actions.",
        "roles_responsibilities": "Manage cloud resources, optimize Docker builds, automate CI/CD deployments, monitor server health.",
        "benefits": "On-call allowances, Certification reimbursement, Premium health care.",
        "education_requirement": "B.Tech / Equivalent Experience",
        "experience_min": 3,
        "experience_max": 6,
        "salary_min": Decimal("1100000.00"),
        "salary_max": Decimal("1600000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.HYBRID,
        "city": "Hyderabad",
        "required_skills": ["AWS", "Docker", "Kubernetes", "Linux"],
        "preferred_skills": ["Git", "Python"],
        "days_ago_posted": 28,
    },
    {
        "index": 8,
        "title": "QA Automation Engineer",
        "role_key": "qa",
        "description": "Quality assurance team requires an Automation Engineer to design automated test suites for web applications.",
        "requirements": "Experience with Selenium/Playwright in Python, Pytest, REST API testing (Postman), and Git CI integration.",
        "roles_responsibilities": "Write test cases, build automated UI/API scripts, log bugs, conduct sanity and regression testing.",
        "benefits": "Flexible leave policy, Medical insurance, Skill upgrade allowance.",
        "education_requirement": "B.Tech / MCA",
        "experience_min": 2,
        "experience_max": 5,
        "salary_min": Decimal("650000.00"),
        "salary_max": Decimal("1000000.00"),
        "vacancies": 3,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.HYBRID,
        "city": "Hyderabad",
        "required_skills": ["Python", "REST APIs", "SQL"],
        "preferred_skills": ["Git", "Linux"],
        "days_ago_posted": 25,
    },
    {
        "index": 9,
        "title": "Software Support Engineer",
        "role_key": "support",
        "description": "Customer Success & Tech Operations team requires a Support Engineer to diagnose technical issues and run DB queries.",
        "requirements": "Good knowledge of Linux command line, SQL queries, REST API troubleshooting, and ticketing systems.",
        "roles_responsibilities": "Analyze error logs, execute SQL scripts, triage customer tickets, collaborate with dev teams for bug fixes.",
        "benefits": "Shift allowances, Health cover, Annual incentive.",
        "education_requirement": "B.Sc/B.Tech/BCA",
        "experience_min": 1,
        "experience_max": 3,
        "salary_min": Decimal("450000.00"),
        "salary_max": Decimal("700000.00"),
        "vacancies": 2,
        "employment_type": EmploymentType.FULL_TIME,
        "work_mode": WorkMode.ONSITE,
        "city": "Hyderabad",
        "required_skills": ["Linux", "SQL", "REST APIs"],
        "preferred_skills": ["Git"],
        "days_ago_posted": 20,
    },
]


class Command(BaseCommand):
    help = "Seeds the database with realistic IT domain recruitment demo data and 90-day guarantee refund claim scenarios."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help="Password for all demo users",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting IT Domain Demo Data Seeding..."))
        password = options.get("password", DEMO_PASSWORD)
        random.seed(42)

        # Suppress actual email sending during demo creation
        with patch("django.core.mail.send_mail"), patch("apps.notifications.services.outbox_processor.OutboxProcessorService.process_batch"):

            # Step 1: Ensure Fee Schedule exists for IT Domain
            self._ensure_fee_schedules()

            # Step 2: Seed Dummy Resume File Asset
            dummy_resume = self._create_dummy_resume()

            # Step 3: Seed 10 IT Job Seekers
            job_seekers = self._seed_job_seekers(password, dummy_resume)

            # Step 4: Seed 10 Recruiters & 10 IT Companies
            recruiters, companies = self._seed_recruiters_and_companies(password)

            # Step 5: Seed 10 IT Jobs
            jobs = self._seed_jobs(recruiters, companies)

            # Step 6: Create Applications across Jobs and Pipeline Stages
            applications_summary = self._seed_applications_and_pipeline(job_seekers, jobs)

            # Step 7: Programmatic Invariant Validation
            self._validate_demo_data()

            self.stdout.write(self.style.SUCCESS("\nIT DOMAIN DEMO DATA SEEDED SUCCESSFULLY!\n"))
            self._print_summary_dashboard(job_seekers, recruiters, companies, jobs, applications_summary)

    def _ensure_fee_schedules(self):
        """Ensures FeeSchedule exists for IT recruitment billing."""
        FeeSchedule.objects.get_or_create(
            domain=DomainType.IT,
            defaults={
                "name": "IT Standard Placement Fee Schedule",
                "fee_type": FeeType.FIXED,
                "fixed_amount": Decimal("50000.00"),
                "percentage": Decimal("8.33"),
                "is_active": True,
            },
        )

    def _create_dummy_resume(self) -> StoredFile:
        """Creates a dummy PDF resume stored file object to attach to candidate profiles."""
        import uuid
        dummy_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
        stored_file, _ = StoredFile.all_objects.get_or_create(
            original_filename="it_demo_candidate_resume.pdf",
            defaults={
                "stored_filename": "it_demo_candidate_resume_hash.pdf",
                "storage_path": "resumes/it_demo_candidate_resume_hash.pdf",
                "file_size_bytes": 10240,
                "mime_type": "application/pdf",
                "file_type": StorageFileType.RESUME,
                "storage_backend": StorageBackendType.LOCAL,
                "domain": DomainType.IT,
                "owner_type": "jobseeker",
                "owner_id": dummy_uuid,
                "uploaded_by_id": dummy_uuid,
            },
        )
        if stored_file.is_deleted:
            stored_file.is_deleted = False
            stored_file.save()
        return stored_file

    def _seed_job_seekers(self, password: str, dummy_resume: StoredFile) -> list:
        """Seeds 10 realistic Telugu-named IT Job Seekers with 100% complete profiles."""
        self.stdout.write("Seeding 10 IT Job Seekers...")
        seekers = []

        for data in JOB_SEEKERS_DATA:
            user, created = ITUser.all_objects.get_or_create(
                email=data["email"],
                defaults={
                    "is_active": True,
                    "email_verified": True,
                },
            )
            user.set_password(password)
            user.is_deleted = False
            user.save()

            ITUserRole.objects.get_or_create(
                user=user,
                role=ITUserRoleType.JOB_SEEKER,
                defaults={"is_primary": True},
            )

            profile, _ = JobSeekerProfile.all_objects.get_or_create(
                user=user,
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone": data["phone"],
                    "gender": "male" if data["first_name"] in ["Sai Kiran", "Venkatesh", "Arjun", "Karthik", "Rahul"] else "female",
                    "city": data["city"],
                    "state": data["state"],
                    "country": "India",
                    "headline": data["headline"],
                    "summary": data["summary"],
                    "experience_years": data["experience_years"],
                    "current_location": data["current_location"],
                    "preferred_location": data["preferred_location"],
                    "current_company": data["current_company"],
                    "current_salary": data["current_salary"],
                    "expected_salary": data["expected_salary"],
                    "notice_period_days": data["notice_period_days"],
                    "employment_type_preference": "full_time",
                    "work_mode_preference": "hybrid",
                    "preferred_roles": [data["headline"]],
                    "linkedin_url": f"https://linkedin.com/in/{data['first_name'].lower().replace(' ', '')}{data['last_name'].lower()}",
                    "github_url": f"https://github.com/{data['first_name'].lower().replace(' ', '')}{data['last_name'].lower()}",
                    "portfolio_url": f"https://{data['first_name'].lower().replace(' ', '')}.dev",
                    "resume_file": dummy_resume,
                    "profile_completeness": 100,
                    "profile_completed": True,
                    "profile_status": "active",
                    "profile_visibility": "public",
                },
            )
            if profile.is_deleted:
                profile.is_deleted = False
                profile.resume_file = dummy_resume
                profile.profile_completeness = 100
                profile.profile_completed = True
                profile.save()

            # Attach Education
            JobSeekerEducation.all_objects.get_or_create(
                job_seeker=profile,
                education_level=EducationLevel.DEGREE,
                defaults={
                    "degree": "B.Tech in Computer Science",
                    "institution": "JNTU Hyderabad",
                    "university": "Jawaharlal Nehru Technological University",
                    "field_of_study": "Computer Science & Engineering",
                    "passing_year": 2020 - (5 - data["experience_years"]),
                    "score_type": EducationScoreType.PERCENTAGE,
                    "percentage": Decimal("78.50"),
                    "is_deleted": False,
                },
            )

            # Attach Experience if experienced
            if data["experience_years"] > 0:
                JobSeekerExperience.all_objects.get_or_create(
                    job_seeker=profile,
                    company_name=data["current_company"],
                    title=data["headline"].split("-")[0].strip(),
                    defaults={
                        "employment_type": EmploymentType.FULL_TIME,
                        "location": data["city"],
                        "start_date": timezone.now().date() - timedelta(days=365 * data["experience_years"]),
                        "is_current": True,
                        "description": "Responsible for core software development, REST API design, and team collaboration.",
                        "is_deleted": False,
                    },
                )

            # Attach Projects
            JobSeekerProject.all_objects.get_or_create(
                job_seeker=profile,
                title=f"Enterprise {data['primary_role'].capitalize()} Solution",
                defaults={
                    "description": "Built high throughput cloud web system serving thousands of active business requests.",
                    "technologies": data["skills"],
                    "github_url": f"https://github.com/demo/{data['primary_role']}-app",
                    "is_deleted": False,
                },
            )

            # Attach Skills
            for skill_name in data["skills"]:
                skill, _ = Skill.all_objects.get_or_create(
                    name=skill_name,
                    defaults={"category": "IT Skills", "is_active": True},
                )
                if skill.is_deleted:
                    skill.is_deleted = False
                    skill.save()

                seeker_skill, _ = JobSeekerSkill.all_objects.get_or_create(
                    job_seeker=profile,
                    skill=skill,
                    defaults={"proficiency_level": 4, "years_of_experience": data["experience_years"]},
                )
                if seeker_skill.is_deleted:
                    seeker_skill.is_deleted = False
                    seeker_skill.save()

            seekers.append(profile)

        return seekers

    def _seed_recruiters_and_companies(self, password: str) -> tuple:
        """Seeds 10 Telugu-named Recruiters and 10 fictional IT Companies."""
        self.stdout.write("Seeding 10 Recruiters & 10 IT Companies...")
        recruiters = []
        companies = []

        for data in RECRUITERS_COMPANIES_DATA:
            user, created = ITUser.all_objects.get_or_create(
                email=data["email"],
                defaults={
                    "is_active": True,
                    "email_verified": True,
                },
            )
            user.set_password(password)
            user.is_deleted = False
            user.save()

            ITUserRole.objects.get_or_create(
                user=user,
                role=ITUserRoleType.RECRUITER,
                defaults={"is_primary": True},
            )

            recruiter, _ = RecruiterProfile.all_objects.get_or_create(
                user=user,
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone": data["phone"],
                    "official_email": data["email"],
                    "designation": data["designation"],
                    "department": "Human Resources",
                    "company_association": data["company_name"],
                    "profile_status": "active",
                    "profile_visibility": "public",
                },
            )
            if recruiter.is_deleted:
                recruiter.is_deleted = False
                recruiter.save()

            # Create Company
            company_slug = data["company_name"].lower().replace("[demo-it]", "").strip().replace(" ", "-")
            company, _ = Company.all_objects.get_or_create(
                slug=company_slug,
                defaults={
                    "name": data["company_name"],
                    "legal_name": data["company_name"].replace("[DEMO-IT] ", "") + " Private Limited",
                    "description": f"{data['company_name']} is a leading technology solutions provider specializing in {data['industry']}.",
                    "industry": data["industry"],
                    "company_size": CompanySize.SIZE_51_200,
                    "website_url": data["website"],
                    "email": f"contact@{company_slug}.demo",
                    "phone": data["phone"],
                    "headquarters_location": f"{data['city']}, Telangana, India",
                    "city": data["city"],
                    "state": "Telangana",
                    "country": "India",
                    "is_active": True,
                },
            )
            if company.is_deleted or not company.is_active:
                company.is_deleted = False
                company.is_active = True
                company.save()

            # Bind Recruiter as Owner of Company
            CompanyMember.all_objects.get_or_create(
                company=company,
                recruiter=recruiter,
                defaults={
                    "role": CompanyMemberRole.OWNER,
                    "is_primary": True,
                    "is_active": True,
                },
            )

            recruiters.append(recruiter)
            companies.append(company)

        return recruiters, companies

    def _seed_jobs(self, recruiters: list, companies: list) -> list:
        """Seeds 10 realistic IT Job Postings."""
        self.stdout.write("Seeding 10 IT Job Postings...")
        jobs = []
        now = timezone.now()

        for data in JOBS_DATA:
            recruiter = recruiters[data["index"]]
            company = companies[data["index"]]
            posted_date = now - timedelta(days=data["days_ago_posted"])

            slug_base = f"{company.slug}-{data['title'].lower().replace(' ', '-')}"
            job, _ = JobPosting.all_objects.get_or_create(
                company=company,
                slug=slug_base,
                defaults={
                    "posted_by": recruiter,
                    "title": data["title"],
                    "job_code": f"IT-JOB-{1000 + data['index']}",
                    "category": "Software Engineering",
                    "department": "Engineering",
                    "description": data["description"],
                    "requirements": data["requirements"],
                    "roles_responsibilities": data["roles_responsibilities"],
                    "benefits": data["benefits"],
                    "education_requirement": data["education_requirement"],
                    "employment_type": data["employment_type"],
                    "work_mode": data["work_mode"],
                    "experience_min": data["experience_min"],
                    "experience_max": data["experience_max"],
                    "salary_min": data["salary_min"],
                    "salary_max": data["salary_max"],
                    "salary_currency": "INR",
                    "salary_visibility": SalaryVisibility.VISIBLE,
                    "vacancies": data["vacancies"],
                    "location": data["city"],
                    "city": data["city"],
                    "state": "Telangana" if data["city"] != "Remote" else "",
                    "country": "India",
                    "status": JobStatus.PUBLISHED,
                    "published_at": posted_date,
                    "expires_at": posted_date + timedelta(days=60),
                    "company_name_snapshot": company.name,
                },
            )

            if job.is_deleted or job.status != JobStatus.PUBLISHED:
                job.is_deleted = False
                job.status = JobStatus.PUBLISHED
                job.published_at = posted_date
                job.save()

            # Attach Required & Preferred Skills
            for s_name in data["required_skills"]:
                skill, _ = Skill.all_objects.get_or_create(name=s_name, defaults={"category": "IT Skills"})
                JobPostingSkill.all_objects.get_or_create(
                    job_posting=job,
                    skill=skill,
                    defaults={"is_preferred": False, "is_deleted": False},
                )

            for s_name in data["preferred_skills"]:
                skill, _ = Skill.all_objects.get_or_create(name=s_name, defaults={"category": "IT Skills"})
                JobPostingSkill.all_objects.get_or_create(
                    job_posting=job,
                    skill=skill,
                    defaults={"is_preferred": True, "is_deleted": False},
                )

            # Job location
            JobLocation.all_objects.get_or_create(
                job_posting=job,
                defaults={
                    "city": data["city"],
                    "country": "India",
                    "work_mode": data["work_mode"],
                    "is_primary": True,
                    "is_deleted": False,
                },
            )

            jobs.append(job)

        return jobs

    def _seed_applications_and_pipeline(self, seekers: list, jobs: list) -> dict:
        """
        Creates 35–40 total applications across jobs and distributes candidate recruitment pipeline:
        - Applied
        - Under Review
        - Shortlisted
        - Interview Scheduled / Interview Completed
        - Selected
        - Joining in Progress / Joined
        - Rejected
        - Withdrawn
        - Absconded Candidate & 90-day Guarantee Refund Claim
        """
        self.stdout.write("Seeding Applications & Recruitment Pipeline Stages...")

        now = timezone.now()
        stats = {
            "total_applications": 0,
            "applied": 0,
            "under_review": 0,
            "shortlisted": 0,
            "interviews": 0,
            "selected": 0,
            "joined": 0,
            "rejected": 0,
            "withdrawn": 0,
            "absconded": 0,
            "claims": 0,
        }

        # Application plan across candidate index & job index
        # We will create 37 targeted applications matching candidate roles to jobs
        app_plan = [
            # Seeker 0 (Sai Kiran - Python 4 yrs): Python job(0), Backend job(1), Fullstack job(3), QA job(8)
            (0, 0, JobApplicationStatus.JOINED),  # Special candidate: Placed & Absconded -> Refund Claim Eligible!
            (0, 1, JobApplicationStatus.SHORTLISTED),
            (0, 3, JobApplicationStatus.INTERVIEW_SCHEDULED),
            (0, 8, JobApplicationStatus.REJECTED),
            # Seeker 1 (Anusha - React 3 yrs): React job(2), Fullstack job(3), QA job(8)
            (1, 2, JobApplicationStatus.JOINED),  # Special candidate 2: Placed & Absconded -> Refund Claim Approved!
            (1, 3, JobApplicationStatus.SELECTED),
            (1, 8, JobApplicationStatus.UNDER_REVIEW),
            # Seeker 2 (Venkatesh - Backend 1 yr): Python job(0), Backend job(1), Support job(9)
            (2, 1, JobApplicationStatus.JOINING_IN_PROGRESS),
            (2, 0, JobApplicationStatus.APPLIED),
            (2, 9, JobApplicationStatus.SHORTLISTED),
            # Seeker 3 (Nikhila - Data 2 yrs): Data job(5), ML job(6), Support job(9)
            (3, 5, JobApplicationStatus.SELECTED),
            (3, 6, JobApplicationStatus.APPLIED),
            (3, 9, JobApplicationStatus.UNDER_REVIEW),
            # Seeker 4 (Arjun - DevOps 5 yrs): DevOps job(7), Java job(4), Python job(0)
            (4, 7, JobApplicationStatus.JOINED),  # Placed candidate active!
            (4, 4, JobApplicationStatus.REJECTED),
            (4, 0, JobApplicationStatus.WITHDRAWN),
            # Seeker 5 (Swathi - Java 5 yrs): Java job(4), Backend job(1), DevOps job(7)
            (5, 4, JobApplicationStatus.INTERVIEW_COMPLETED),
            (5, 1, JobApplicationStatus.SHORTLISTED),
            (5, 7, JobApplicationStatus.APPLIED),
            # Seeker 6 (Karthik - ML 3 yrs): ML job(6), Data job(5), Python job(0)
            (6, 6, JobApplicationStatus.INTERVIEW_SCHEDULED),
            (6, 5, JobApplicationStatus.UNDER_REVIEW),
            (6, 0, JobApplicationStatus.APPLIED),
            # Seeker 7 (Harika - QA 3 yrs): QA job(8), Python job(0), Support job(9)
            (7, 8, JobApplicationStatus.SHORTLISTED),
            (7, 0, JobApplicationStatus.APPLIED),
            (7, 9, JobApplicationStatus.REJECTED),
            # Seeker 8 (Rahul - Support 2 yrs): Support job(9), Backend job(1), QA job(8)
            (8, 9, JobApplicationStatus.APPLIED),
            (8, 1, JobApplicationStatus.UNDER_REVIEW),
            (8, 8, JobApplicationStatus.WITHDRAWN),
            # Seeker 9 (Divya Sri - Fullstack 3 yrs): Fullstack job(3), React job(2), Python job(0), Java job(4)
            (9, 3, JobApplicationStatus.INTERVIEW_COMPLETED),
            (9, 2, JobApplicationStatus.SHORTLISTED),
            (9, 0, JobApplicationStatus.APPLIED),
            (9, 4, JobApplicationStatus.REJECTED),
            # Additional applications to reach ~38 total
            (0, 5, JobApplicationStatus.APPLIED),
            (1, 0, JobApplicationStatus.APPLIED),
            (2, 3, JobApplicationStatus.REJECTED),
            (3, 0, JobApplicationStatus.APPLIED),
            (6, 3, JobApplicationStatus.UNDER_REVIEW),
        ]

        for seeker_idx, job_idx, final_status in app_plan:
            seeker = seekers[seeker_idx]
            job = jobs[job_idx]

            # Determine chronological timestamps based on job posted date
            job_posted = job.published_at
            applied_at = job_posted + timedelta(days=random.randint(1, 10))

            app, created = JobApplication.all_objects.get_or_create(
                job_posting=job,
                job_seeker=seeker,
                defaults={
                    "company": job.company,
                    "resume_file": seeker.resume_file,
                    "cover_letter": f"Dear Hiring Team at {job.company.name},\n\nI am excited to apply for the position of {job.title}. My background aligns well with your requirements.\n\nBest regards,\n{seeker.full_name}",
                    "expected_salary": seeker.expected_salary,
                    "notice_period": f"{seeker.notice_period_days} Days",
                    "current_location": seeker.current_location,
                    "source": ApplicationSource.DIRECT,
                    "status": JobApplicationStatus.APPLIED,
                    "applied_at": applied_at,
                    "status_changed_at": applied_at,
                    "applicant_name_snapshot": seeker.full_name,
                    "job_title_snapshot": job.title,
                    "company_name_snapshot": job.company.name,
                },
            )

            if app.is_deleted:
                app.is_deleted = False
                app.status = JobApplicationStatus.APPLIED
                app.applied_at = applied_at
                app.save()

            stats["total_applications"] += 1
            curr_time = applied_at

            # Add status history & timeline event for APPLIED
            JobApplicationStatusHistory.objects.get_or_create(
                application=app,
                to_status=JobApplicationStatus.APPLIED,
                defaults={
                    "from_status": None,
                    "changed_by_id": seeker.user_id,
                    "notes": "Application submitted by job seeker.",
                    "changed_at": curr_time,
                },
            )

            # Advance status according to final_status
            if final_status == JobApplicationStatus.APPLIED:
                stats["applied"] += 1
                continue

            # Move to UNDER_REVIEW
            curr_time += timedelta(days=random.randint(1, 3))
            self._transition_app_status(app, JobApplicationStatus.APPLIED, JobApplicationStatus.UNDER_REVIEW, curr_time, job.posted_by.user_id, "Application moved to Under Review by recruiter.")
            if final_status == JobApplicationStatus.UNDER_REVIEW:
                stats["under_review"] += 1
                continue

            # Move to REJECTED if applicable here
            if final_status == JobApplicationStatus.REJECTED:
                curr_time += timedelta(days=random.randint(1, 3))
                self._transition_app_status(app, JobApplicationStatus.UNDER_REVIEW, JobApplicationStatus.REJECTED, curr_time, job.posted_by.user_id, "Candidate qualifications do not match role requirements.")
                stats["rejected"] += 1
                continue

            # Move to WITHDRAWN if applicable
            if final_status == JobApplicationStatus.WITHDRAWN:
                curr_time += timedelta(days=random.randint(1, 3))
                self._transition_app_status(app, JobApplicationStatus.UNDER_REVIEW, JobApplicationStatus.WITHDRAWN, curr_time, seeker.user_id, "Candidate withdrew application due to another offer.")
                stats["withdrawn"] += 1
                continue

            # Move to SHORTLISTED
            curr_time += timedelta(days=random.randint(1, 3))
            self._transition_app_status(app, JobApplicationStatus.UNDER_REVIEW, JobApplicationStatus.SHORTLISTED, curr_time, job.posted_by.user_id, "Candidate shortlisted for technical interview.")
            if final_status == JobApplicationStatus.SHORTLISTED:
                stats["shortlisted"] += 1
                continue

            # Schedule Interview
            curr_time += timedelta(days=random.randint(2, 4))
            interview_date = curr_time + timedelta(days=2)
            self._transition_app_status(app, JobApplicationStatus.SHORTLISTED, JobApplicationStatus.INTERVIEW_SCHEDULED, curr_time, job.posted_by.user_id, "Technical interview round scheduled.")
            
            interview, _ = JobApplicationInterview.all_objects.get_or_create(
                application=app,
                round_type=InterviewRoundType.TECHNICAL,
                defaults={
                    "domain": DomainType.IT,
                    "interview_type": "Technical Round 1",
                    "round_label": "Technical Deep Dive",
                    "mode": InterviewMode.ONLINE,
                    "scheduled_at": interview_date,
                    "duration_minutes": 60,
                    "meet_url": f"https://meet.google.com/demo-it-{app.pk.hex[:6]}",
                    "instructions": "Please join 5 mins before schedule with camera turned on.",
                    "status": InterviewStatus.COMPLETED if final_status in [JobApplicationStatus.INTERVIEW_COMPLETED, JobApplicationStatus.SELECTED, JobApplicationStatus.JOINING_IN_PROGRESS, JobApplicationStatus.JOINED] else InterviewStatus.SCHEDULED,
                    "candidate_confirmed": True,
                    "scheduled_by_id": job.posted_by.user_id,
                },
            )

            if final_status == JobApplicationStatus.INTERVIEW_SCHEDULED:
                stats["interviews"] += 1
                continue

            # Complete Interview with Evaluation
            curr_time = interview_date + timedelta(hours=2)
            self._transition_app_status(app, JobApplicationStatus.INTERVIEW_SCHEDULED, JobApplicationStatus.INTERVIEW_COMPLETED, curr_time, job.posted_by.user_id, "Technical interview completed successfully.")
            
            InterviewEvaluation.all_objects.get_or_create(
                domain=DomainType.IT,
                application_id=app.pk,
                defaults={
                    "technical_rating": 4,
                    "communication_rating": 4,
                    "subject_knowledge": 5,
                    "industry_skills": 4,
                    "culture_fit": 4,
                    "overall_rating": 4,
                    "interview_notes": "Candidate performed well in problem solving, data structures, and system design.",
                    "recommendation": "select",
                    "created_by_id": job.posted_by.user_id,
                },
            )

            if final_status == JobApplicationStatus.INTERVIEW_COMPLETED:
                stats["interviews"] += 1
                continue

            # Select Candidate
            curr_time += timedelta(days=random.randint(1, 3))
            self._transition_app_status(app, JobApplicationStatus.INTERVIEW_COMPLETED, JobApplicationStatus.SELECTED, curr_time, job.posted_by.user_id, "Candidate selected and formal offer released.")
            
            ctc = seeker.expected_salary or Decimal("1000000.00")
            placement_details, _ = PlacementDetails.all_objects.get_or_create(
                domain=DomainType.IT,
                application_id=app.pk,
                defaults={
                    "selected_at": curr_time,
                    "selected_by_id": job.posted_by.user_id,
                    "offered_designation": job.title,
                    "department": "Engineering",
                    "work_location": job.location,
                    "employment_type": "Full-Time",
                    "agreed_salary": ctc,
                    "offer_reference_number": f"OFF-IT-{app.pk.hex[:6].upper()}",
                },
            )

            # Generate Invoice
            invoice = self._create_invoice_for_placement(app, job, seeker, ctc, curr_time)

            if final_status == JobApplicationStatus.SELECTED:
                stats["selected"] += 1
                continue

            # Move to JOINING_IN_PROGRESS or JOINED
            if final_status == JobApplicationStatus.JOINING_IN_PROGRESS:
                curr_time += timedelta(days=random.randint(2, 5))
                self._transition_app_status(app, JobApplicationStatus.SELECTED, JobApplicationStatus.JOINING_IN_PROGRESS, curr_time, job.posted_by.user_id, "Candidate accepted offer; onboarding in progress.")
                placement_details.expected_joining_date = curr_time.date() + timedelta(days=15)
                placement_details.save()
                stats["selected"] += 1
                continue

            if final_status == JobApplicationStatus.JOINED:
                # Calculate actual joining date backdated
                # For Seeker 0 (Eligible Pending Claim): joined 28 days ago, absconded 8 days ago
                # For Seeker 1 (Approved Claim): joined 70 days ago, absconded 30 days ago
                # For Seeker 4 (Regular Joined Candidate): joined 15 days ago, active working
                if seeker_idx == 0:
                    joined_date = now.date() - timedelta(days=28)
                elif seeker_idx == 1:
                    joined_date = now.date() - timedelta(days=70)
                else:
                    joined_date = now.date() - timedelta(days=15)

                joined_dt = timezone.make_aware(timezone.datetime.combine(joined_date, timezone.datetime.min.time()))

                self._transition_app_status(app, JobApplicationStatus.SELECTED, JobApplicationStatus.JOINED, joined_dt, job.posted_by.user_id, "Candidate confirmed joined on-site.")
                app.placed_at = joined_dt
                app.hired_at = joined_dt
                app.save(update_fields=["placed_at", "hired_at"])

                placement_details.actual_joining_date = joined_date
                placement_details.joined_at = joined_dt
                placement_details.joined_by_id = job.posted_by.user_id
                placement_details.employee_id = f"EMP-{app.pk.hex[:6].upper()}"
                placement_details.save()

                # Start 90-day Placement Guarantee
                guarantee = self._create_placement_guarantee(invoice, app, joined_dt)

                stats["joined"] += 1

                # ABSCONDED & REFUND CLAIM SCENARIOS
                if seeker_idx == 0:
                    # SCENARIO A: Candidate absconds 8 days ago (within 90-day window!). Recruiter files refund claim (Pending).
                    abscond_date = now.date() - timedelta(days=8)
                    abscond_dt = timezone.make_aware(timezone.datetime.combine(abscond_date, timezone.datetime.min.time()))

                    guarantee.status = GuaranteeStatus.ACTIVE
                    guarantee.save(update_fields=["status"])

                    # Create Pending Refund Claim
                    claim, _ = GuaranteeClaim.all_objects.update_or_create(
                        claim_number="CLM-DEMO-IT-001",
                        defaults={
                            "domain": DomainType.IT,
                            "recruiter_id": job.posted_by.user_id,
                            "institution_id": None,
                            "guarantee_id": guarantee.pk,
                            "application_entity_type": "jobapplication",
                            "application_entity_id": app.pk,
                            "placement_fee_id": app.pk,
                            "invoice_id": invoice.pk,
                            "joining_date": joined_date,
                            "guarantee_start_date": joined_date,
                            "guarantee_end_date": joined_date + timedelta(days=90),
                            "exit_date": abscond_date,
                            "exit_reason": ExitReason.ABSCONDED,
                            "claim_type": ClaimType.REFUND,
                            "status": ClaimStatus.SUBMITTED,
                            "reason": "Candidate absconded without notice 20 days after joining. Requesting 100% placement fee refund under 90-day policy guarantee.",
                            "claim_description": "Candidate stopped reporting to office on " + abscond_date.strftime("%Y-%m-%d") + ". HR attempts to contact remained unanswered.",
                            "submitted_at": abscond_dt + timedelta(days=1),
                            "refund_amount": invoice.total_amount,
                            "is_deleted": False,
                        },
                    )

                    GuaranteeClaimHistory.objects.get_or_create(
                        claim=claim,
                        to_status=ClaimStatus.SUBMITTED,
                        defaults={
                            "from_status": None,
                            "changed_by_id": job.posted_by.user_id,
                            "notes": "Refund claim submitted by recruiter following candidate absconding.",
                            "changed_at": abscond_dt + timedelta(days=1),
                        },
                    )

                    stats["absconded"] += 1
                    stats["claims"] += 1

                elif seeker_idx == 1:
                    # SCENARIO B: Candidate joined 70 days ago, absconded 30 days ago. Refund claim was reviewed and APPROVED.
                    abscond_date = now.date() - timedelta(days=30)
                    abscond_dt = timezone.make_aware(timezone.datetime.combine(abscond_date, timezone.datetime.min.time()))

                    guarantee.status = GuaranteeStatus.CLOSED
                    guarantee.save(update_fields=["status"])

                    claim, _ = GuaranteeClaim.all_objects.update_or_create(
                        claim_number="CLM-DEMO-IT-002",
                        defaults={
                            "domain": DomainType.IT,
                            "recruiter_id": job.posted_by.user_id,
                            "institution_id": None,
                            "guarantee_id": guarantee.pk,
                            "application_entity_type": "jobapplication",
                            "application_entity_id": app.pk,
                            "placement_fee_id": app.pk,
                            "invoice_id": invoice.pk,
                            "joining_date": joined_date,
                            "guarantee_start_date": joined_date,
                            "guarantee_end_date": joined_date + timedelta(days=90),
                            "exit_date": abscond_date,
                            "exit_reason": ExitReason.ABSCONDED,
                            "claim_type": ClaimType.REFUND,
                            "status": ClaimStatus.APPROVED,
                            "reason": "Candidate absconded 40 days after joining. Guarantee claim verified and eligible.",
                            "claim_description": "Official absconding confirmation submitted with exit feedback.",
                            "submitted_at": abscond_dt + timedelta(days=1),
                            "reviewed_at": abscond_dt + timedelta(days=3),
                            "approval_date": abscond_dt + timedelta(days=4),
                            "approved_by_id": job.posted_by.user_id,
                            "review_notes": "Absconding verified against company attendance logs. Refund approved under 90-day window.",
                            "refund_amount": invoice.total_amount,
                            "is_deleted": False,
                        },
                    )

                    GuaranteeClaimHistory.objects.get_or_create(
                        claim=claim,
                        to_status=ClaimStatus.APPROVED,
                        defaults={
                            "from_status": ClaimStatus.SUBMITTED,
                            "changed_by_id": job.posted_by.user_id,
                            "notes": "Claim approved by SuperAdmin.",
                            "changed_at": abscond_dt + timedelta(days=4),
                        },
                    )

                    stats["absconded"] += 1
                    stats["claims"] += 1

        return stats

    def _transition_app_status(self, app: JobApplication, from_st: str, to_st: str, ts: timezone.datetime, actor_id, notes: str):
        """Safely updates application status, status history, and timeline events."""
        app.status = to_st
        app.status_changed_at = ts
        app.save(update_fields=["status", "status_changed_at", "updated_at"])

        JobApplicationStatusHistory.objects.create(
            application=app,
            from_status=from_st,
            to_status=to_st,
            changed_by_id=actor_id,
            notes=notes,
            changed_at=ts,
        )

        JobApplicationTimelineEvent.objects.create(
            application=app,
            event_type=TimelineEventType.STATUS_CHANGED,
            from_status=from_st,
            to_status=to_st,
            actor_id=actor_id,
            actor_domain=DomainType.IT,
            notes=notes,
            occurred_at=ts,
        )

    def _create_invoice_for_placement(self, app: JobApplication, job: JobPosting, seeker: JobSeekerProfile, ctc: Decimal, ts: timezone.datetime) -> Invoice:
        """Creates placement fee invoice record."""
        placement_fee_id = app.pk
        service_fee = ctc * Decimal("0.0833")  # 8.33% standard recruitment fee
        tax_amount = service_fee * Decimal("0.18")  # 18% GST
        total_amount = service_fee + tax_amount

        invoice, _ = Invoice.all_objects.get_or_create(
            domain=DomainType.IT,
            placement_fee_id=placement_fee_id,
            defaults={
                "invoice_number": f"INV-IT-{app.pk.hex[:8].upper()}",
                "bill_to_entity_type": EntityReferenceType.IT_COMPANY,
                "bill_to_entity_id": job.company_id,
                "bill_to_name_snapshot": job.company.name,
                "candidate_annual_ctc": ctc,
                "candidate_name": seeker.full_name,
                "candidate_job_title": job.title,
                "subtotal": service_fee,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "cgst_amount": tax_amount / 2,
                "sgst_amount": tax_amount / 2,
                "taxable_amount": service_fee,
                "currency": "INR",
                "created_by_id": seeker.user_id,
            },
        )
        if invoice.is_deleted:
            invoice.is_deleted = False
            invoice.save()

        InvoiceLineItem.all_objects.get_or_create(
            invoice=invoice,
            description=f"Recruitment Service Fee (8.33% CTC) for {seeker.full_name} ({job.title})",
            defaults={
                "quantity": Decimal("1.00"),
                "unit_price": service_fee,
                "line_total": service_fee,
                "created_by_id": seeker.user_id,
            },
        )

        return invoice

    def _create_placement_guarantee(self, invoice: Invoice, app: JobApplication, joining_dt: timezone.datetime) -> PlacementGuarantee:
        """Creates 90-day Placement Guarantee starting at joining date."""
        starts_at = joining_dt
        expires_at = starts_at + timedelta(days=90)

        guarantee, _ = PlacementGuarantee.all_objects.get_or_create(
            invoice_id=invoice.pk,
            defaults={
                "domain": DomainType.IT,
                "placement_fee_id": app.pk,
                "application_entity_type": EntityReferenceType.IT_JOB_APPLICATION,
                "application_entity_id": app.pk,
                "guarantee_days": 90,
                "starts_at": starts_at,
                "expires_at": expires_at,
                "status": GuaranteeStatus.ACTIVE,
            },
        )
        if guarantee.is_deleted:
            guarantee.is_deleted = False
            guarantee.save()

        return guarantee

    def _validate_demo_data(self):
        """Validates all invariants programmatically after demo data creation."""
        self.stdout.write("Validating demo data invariants...")

        seeker_count = JobSeekerProfile.objects.filter(user__email__startswith="it.seeker").count()
        if seeker_count != 10:
            raise ValueError(f"Expected 10 IT Job Seekers, found {seeker_count}")

        recruiter_count = RecruiterProfile.objects.filter(user__email__startswith="it.recruiter").count()
        if recruiter_count != 10:
            raise ValueError(f"Expected 10 IT Recruiters, found {recruiter_count}")

        company_count = Company.objects.filter(name__startswith="[DEMO-IT]").count()
        if company_count != 10:
            raise ValueError(f"Expected 10 IT Companies, found {company_count}")

        job_count = JobPosting.objects.filter(company__name__startswith="[DEMO-IT]").count()
        if job_count != 10:
            raise ValueError(f"Expected 10 IT Jobs, found {job_count}")

        app_count = JobApplication.objects.filter(job_posting__company__name__startswith="[DEMO-IT]").count()
        if app_count < 30:
            raise ValueError(f"Expected at least 30 Applications, found {app_count}")

        # Check Absconded & Guarantee Claim Scenarios
        claim_count = GuaranteeClaim.objects.filter(claim_number__startswith="CLM-DEMO-IT").count()
        if claim_count < 1:
            raise ValueError(f"Expected at least 1 valid 90-day Guarantee Claim scenario, found {claim_count}")

        # Assert no Faculty domain records were created by this script
        from apps.accounts.models import ProfessorUser, CollegeUser
        from apps.faculty.models import FacultyVacancy
        if ProfessorUser.objects.filter(email__startswith="it.seeker").exists() or FacultyVacancy.objects.filter(title__startswith="[DEMO-IT]").exists():
            raise ValueError("Faculty domain records were illegally created in IT seeder!")

        # Chronology invariant validation for applications
        for app in JobApplication.objects.filter(job_posting__company__name__startswith="[DEMO-IT]"):
            histories = list(app.status_history.order_by("changed_at"))
            for i in range(1, len(histories)):
                if histories[i].changed_at < histories[i - 1].changed_at:
                    raise ValueError(f"Chronology invariant broken on application {app.pk}: {histories[i].changed_at} < {histories[i-1].changed_at}")

        self.stdout.write(self.style.SUCCESS("All invariants validated successfully!"))

    def _print_summary_dashboard(self, seekers, recruiters, companies, jobs, stats):
        """Prints formatted ASCII dashboard summary of created demo dataset."""
        summary = f"""
====================================================
EDUNAUKARI IT DOMAIN DEMO DATA CREATED
====================================================

Users & Profiles
  Job Seekers ................ {len(seekers)}
  Recruiters ................. {len(recruiters)}
  Companies .................. {len(companies)}

Recruitment Pipeline
  Job Posts .................. {len(jobs)}
  Total Applications ......... {stats['total_applications']}
  Applied .................... {stats['applied']}
  Under Review ............... {stats['under_review']}
  Shortlisted ................ {stats['shortlisted']}
  Interviews Scheduled ....... {stats['interviews']}
  Selected ................... {stats['selected']}
  Joined / Placed ............ {stats['joined']}
  Rejected ................... {stats['rejected']}
  Withdrawn .................. {stats['withdrawn']}
  Absconded Candidates ....... {stats['absconded']}

Guarantee & Refund Claims (90-Day Policy)
  Eligible Refund Claims ..... {stats['claims']}
  Pending Refund Claims ...... 1  (CLM-DEMO-IT-001)
  Approved Refund Claims ..... 1  (CLM-DEMO-IT-002)

Demo Account Password
  Password ................... {DEMO_PASSWORD}

Sample Candidate Email
  it.seeker01.saikiran@example.com

Sample Recruiter Email
  it.recruiter01.sravani@example.com

====================================================
"""
        self.stdout.write(summary)


if __name__ == "__main__":
    Command().handle()
