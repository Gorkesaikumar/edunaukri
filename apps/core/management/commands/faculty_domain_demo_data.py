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

from apps.accounts.models import ProfessorUser, CollegeUser
from apps.academic_recruitment.models import ProfessorProfile, Qualification, ProfessorQualification
from apps.colleges.models import College, CollegeMember
from apps.colleges.constants.enums import InstitutionType, OwnershipType, CollegeMemberRole
from apps.faculty.models import FacultyVacancy
from apps.faculty.constants.enums import Designation, QualificationLevel, VacancyStatus
from apps.applications.models import (
    FacultyApplication,
    FacultyApplicationStatusHistory,
    FacultyApplicationTimelineEvent,
    InterviewEvaluation,
    PlacementDetails,
)
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.constants.enums import ApplicationSource, TimelineEventType
from apps.applications.constants.interview_enums import InterviewRoundType, InterviewMode, InterviewStatus
from apps.billing.models import FeeSchedule, PlacementFee
from apps.billing.constants.enums import FeeType
from apps.invoices.models import Invoice, InvoiceLineItem
from apps.guarantee_claims.models import PlacementGuarantee, GuaranteeClaim, GuaranteeClaimHistory
from apps.guarantee_claims.constants.enums import ClaimStatus, ClaimType, ExitReason, GuaranteeStatus
from apps.documents.models import StoredFile
from apps.documents.constants.enums import StorageFileType, StorageBackendType
from apps.core.constants.enums import DomainType, EntityReferenceType

DEMO_PASSWORD = "Demo@12345"

# Realistic Telugu-named Faculty candidates dataset
FACULTY_CANDIDATES_DATA = [
    {
        "email": "faculty.candidate01.saikrishna@example.com",
        "first_name": "Sai Krishna",
        "last_name": "Reddy",
        "phone": "+919849011001",
        "highest_qualification": "M.Tech",
        "specialization": "Computer Science & Engineering",
        "research_interests": "Cloud Computing, Distributed Systems, Algorithms",
        "experience_years": 6,
        "teaching_experience_years": 6,
        "industry_experience_years": 0,
        "publications_count": 4,
        "current_designation": "Assistant Professor",
        "current_institution": "Sri Indu College of Engineering",
        "expected_salary": Decimal("750000.00"),
        "preferred_locations": "Hyderabad, Secunderabad",
        "city": "Hyderabad",
    },
    {
        "email": "faculty.candidate02.sravani@example.com",
        "first_name": "Sravani",
        "last_name": "Goud",
        "phone": "+919849011002",
        "highest_qualification": "M.Sc",
        "specialization": "Computer Science",
        "research_interests": "Web Technologies, Database Management Systems",
        "experience_years": 4,
        "teaching_experience_years": 4,
        "industry_experience_years": 0,
        "publications_count": 2,
        "current_designation": "Lecturer",
        "current_institution": "Kakatiya Degree College",
        "expected_salary": Decimal("550000.00"),
        "preferred_locations": "Warangal, Hanamkonda",
        "city": "Warangal",
    },
    {
        "email": "faculty.candidate03.venkatesh@example.com",
        "first_name": "Venkatesh",
        "last_name": "Rao",
        "phone": "+919849011003",
        "highest_qualification": "PhD",
        "specialization": "Computer Science & Artificial Intelligence",
        "research_interests": "Machine Learning, Deep Learning, Computer Vision",
        "experience_years": 8,
        "teaching_experience_years": 8,
        "industry_experience_years": 2,
        "publications_count": 9,
        "current_designation": "Associate Professor",
        "current_institution": "SR University",
        "expected_salary": Decimal("1100000.00"),
        "preferred_locations": "Hyderabad, Warangal",
        "city": "Hyderabad",
    },
    {
        "email": "faculty.candidate04.harika@example.com",
        "first_name": "Harika",
        "last_name": "Devi",
        "phone": "+919849011004",
        "highest_qualification": "M.A",
        "specialization": "English Literature & Phonetics",
        "research_interests": "Indian English Literature, Business Communication",
        "experience_years": 5,
        "teaching_experience_years": 5,
        "industry_experience_years": 0,
        "publications_count": 3,
        "current_designation": "Assistant Professor",
        "current_institution": "Gitam University Hyderabad Campus",
        "expected_salary": Decimal("600000.00"),
        "preferred_locations": "Hyderabad, Nizamabad",
        "city": "Nizamabad",
    },
    {
        "email": "faculty.candidate05.naveen@example.com",
        "first_name": "Naveen",
        "last_name": "Kumar",
        "phone": "+919849011005",
        "highest_qualification": "M.Sc",
        "specialization": "Applied Mathematics",
        "research_interests": "Differential Equations, Numerical Analysis",
        "experience_years": 3,
        "teaching_experience_years": 3,
        "industry_experience_years": 0,
        "publications_count": 1,
        "current_designation": "Lecturer",
        "current_institution": "SRR Government Degree College",
        "expected_salary": Decimal("480000.00"),
        "preferred_locations": "Karimnagar, Hyderabad",
        "city": "Karimnagar",
    },
    {
        "email": "faculty.candidate06.keerthana@example.com",
        "first_name": "Keerthana",
        "last_name": "Reddy",
        "phone": "+919849011006",
        "highest_qualification": "MBA",
        "specialization": "Finance & Human Resource Management",
        "research_interests": "Corporate Governance, Talent Acquisition Strategies",
        "experience_years": 4,
        "teaching_experience_years": 4,
        "industry_experience_years": 1,
        "publications_count": 2,
        "current_designation": "Assistant Professor",
        "current_institution": "Vignana Jyothi Institute of Management",
        "expected_salary": Decimal("650000.00"),
        "preferred_locations": "Hyderabad, Vijayawada",
        "city": "Hyderabad",
    },
    {
        "email": "faculty.candidate07.praveen@example.com",
        "first_name": "Praveen",
        "last_name": "Naidu",
        "phone": "+919849011007",
        "highest_qualification": "MCA",
        "specialization": "Computer Applications & Database Systems",
        "research_interests": "Software Engineering, Relational Databases",
        "experience_years": 2,
        "teaching_experience_years": 2,
        "industry_experience_years": 0,
        "publications_count": 1,
        "current_designation": "Lecturer",
        "current_institution": "KITS Khammam",
        "expected_salary": Decimal("420000.00"),
        "preferred_locations": "Khammam, Hyderabad",
        "city": "Khammam",
    },
    {
        "email": "faculty.candidate08.divyasri@example.com",
        "first_name": "Divya",
        "last_name": "Sri",
        "phone": "+919849011008",
        "highest_qualification": "PhD",
        "specialization": "Business Management & Marketing",
        "research_interests": "Consumer Behavior, Strategic Brand Management",
        "experience_years": 7,
        "teaching_experience_years": 7,
        "industry_experience_years": 2,
        "publications_count": 6,
        "current_designation": "Assistant Professor",
        "current_institution": "KL University",
        "expected_salary": Decimal("900000.00"),
        "preferred_locations": "Vijayawada, Visakhapatnam",
        "city": "Vijayawada",
    },
    {
        "email": "faculty.candidate09.anusha@example.com",
        "first_name": "Anusha",
        "last_name": "Reddy",
        "phone": "+919849011009",
        "highest_qualification": "M.Sc",
        "specialization": "Physics & Electronics",
        "research_interests": "Solid State Physics, Semiconductor Devices",
        "experience_years": 1,
        "teaching_experience_years": 1,
        "industry_experience_years": 0,
        "publications_count": 0,
        "current_designation": "Junior Lecturer",
        "current_institution": "Gayatri Vidya Parishad",
        "expected_salary": Decimal("380000.00"),
        "preferred_locations": "Visakhapatnam, Vizianagaram",
        "city": "Visakhapatnam",
    },
    {
        "email": "faculty.candidate10.karthik@example.com",
        "first_name": "Karthik",
        "last_name": "Varma",
        "phone": "+919849011010",
        "highest_qualification": "M.Com",
        "specialization": "Accounting & Taxation",
        "research_interests": "GST Framework, Financial Accounting",
        "experience_years": 3,
        "teaching_experience_years": 3,
        "industry_experience_years": 0,
        "publications_count": 1,
        "current_designation": "Lecturer in Commerce",
        "current_institution": "Aditya Degree College",
        "expected_salary": Decimal("450000.00"),
        "preferred_locations": "Visakhapatnam, Kakinada",
        "city": "Visakhapatnam",
    },
]

# Realistic Faculty Recruiters dataset
FACULTY_RECRUITERS_DATA = [
    {
        "email": "faculty.recruiter01.sirisha@example.com",
        "first_name": "Sirisha",
        "last_name": "Reddy",
        "phone": "+919849022001",
        "designation": "Head of HR & Faculty Recruitment",
    },
    {
        "email": "faculty.recruiter02.ramesh@example.com",
        "first_name": "Ramesh",
        "last_name": "Goud",
        "phone": "+919849022002",
        "designation": "Principal & Member Secretary",
    },
    {
        "email": "faculty.recruiter03.lakshmi@example.com",
        "first_name": "Lakshmi",
        "last_name": "Prasanna",
        "phone": "+919849022003",
        "designation": "Academic Dean",
    },
    {
        "email": "faculty.recruiter04.manoj@example.com",
        "first_name": "Manoj",
        "last_name": "Kumar",
        "phone": "+919849022004",
        "designation": "Director of Management Studies",
    },
    {
        "email": "faculty.recruiter05.swathi@example.com",
        "first_name": "Swathi",
        "last_name": "Rao",
        "phone": "+919849022005",
        "designation": "Academic Coordinator",
    },
    {
        "email": "faculty.recruiter06.sandeep@example.com",
        "first_name": "Sandeep",
        "last_name": "Reddy",
        "phone": "+919849022006",
        "designation": "HOD Science & Humanities",
    },
    {
        "email": "faculty.recruiter07.deepika@example.com",
        "first_name": "Deepika",
        "last_name": "Naidu",
        "phone": "+919849022007",
        "designation": "HR Manager",
    },
    {
        "email": "faculty.recruiter08.raviteja@example.com",
        "first_name": "Ravi",
        "last_name": "Teja",
        "phone": "+919849022008",
        "designation": "Vice Principal",
    },
    {
        "email": "faculty.recruiter09.anjali@example.com",
        "first_name": "Anjali",
        "last_name": "Goud",
        "phone": "+919849022009",
        "designation": "Placement & Staffing Officer",
    },
    {
        "email": "faculty.recruiter10.srikanth@example.com",
        "first_name": "Srikanth",
        "last_name": "Rao",
        "phone": "+919849022010",
        "designation": "Dean of Engineering",
    },
]

# Fictional Educational Institutions dataset
FACULTY_INSTITUTIONS_DATA = [
    {
        "name": "Veda Institute of Technology",
        "slug": "demo-fac-veda-institute-of-technology",
        "institution_type": InstitutionType.ENGINEERING,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Hyderabad",
        "state": "Telangana",
        "website_url": "https://veda-tech.demo.example.com",
        "description": "Leading premier engineering institution focusing on CSE, AI, and IT disciplines.",
        "established_year": 2005,
        "number_of_students": 3200,
        "number_of_faculty": 180,
    },
    {
        "name": "Sree Akshara Degree College",
        "slug": "demo-fac-sree-akshara-degree-college",
        "institution_type": InstitutionType.ARTS_SCIENCE,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Warangal",
        "state": "Telangana",
        "website_url": "https://akshara-degree.demo.example.com",
        "description": "Established degree college offering B.Sc, M.Sc, and Computer Science programs.",
        "established_year": 2010,
        "number_of_students": 1500,
        "number_of_faculty": 65,
    },
    {
        "name": "ManaTech Engineering College",
        "slug": "demo-fac-manatech-engineering-college",
        "institution_type": InstitutionType.ENGINEERING,
        "ownership_type": OwnershipType.AUTONOMOUS,
        "city": "Hyderabad",
        "state": "Telangana",
        "website_url": "https://manatech-eng.demo.example.com",
        "description": "Autonomous engineering college known for state-of-the-art research labs.",
        "established_year": 2001,
        "number_of_students": 4500,
        "number_of_faculty": 240,
    },
    {
        "name": "BlueSky School of Management",
        "slug": "demo-fac-bluesky-school-of-management",
        "institution_type": InstitutionType.MANAGEMENT,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Hyderabad",
        "state": "Telangana",
        "website_url": "https://bluesky-bschool.demo.example.com",
        "description": "Top-ranked management institute offering MBA and Post Graduate Executive Diplomas.",
        "established_year": 2012,
        "number_of_students": 800,
        "number_of_faculty": 45,
    },
    {
        "name": "Pragathi PG College",
        "slug": "demo-fac-pragathi-pg-college",
        "institution_type": InstitutionType.UNIVERSITY,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Nizamabad",
        "state": "Telangana",
        "website_url": "https://pragathi-pg.demo.example.com",
        "description": "Post graduate college specializing in Mathematics, Commerce, and English Studies.",
        "established_year": 2008,
        "number_of_students": 1200,
        "number_of_faculty": 55,
    },
    {
        "name": "Nova Institute of Sciences",
        "slug": "demo-fac-nova-institute-of-sciences",
        "institution_type": InstitutionType.ARTS_SCIENCE,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Karimnagar",
        "state": "Telangana",
        "website_url": "https://nova-sciences.demo.example.com",
        "description": "Institute dedicated to pure and applied sciences including Physics and Mathematics.",
        "established_year": 2014,
        "number_of_students": 950,
        "number_of_faculty": 40,
    },
    {
        "name": "Arya College of Engineering",
        "slug": "demo-fac-arya-college-of-engineering",
        "institution_type": InstitutionType.ENGINEERING,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Khammam",
        "state": "Telangana",
        "website_url": "https://arya-eng.demo.example.com",
        "description": "Progressive engineering institution fostering innovation in Computer Applications.",
        "established_year": 2007,
        "number_of_students": 2200,
        "number_of_faculty": 110,
    },
    {
        "name": "Sahasra Degree & PG College",
        "slug": "demo-fac-sahasra-degree-pg-college",
        "institution_type": InstitutionType.ARTS_SCIENCE,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Vijayawada",
        "state": "Andhra Pradesh",
        "website_url": "https://sahasra-college.demo.example.com",
        "description": "Prominent undergraduate and postgraduate institution in Krishna district.",
        "established_year": 2011,
        "number_of_students": 1800,
        "number_of_faculty": 75,
    },
    {
        "name": "VidyaVeda Academy",
        "slug": "demo-fac-vidyaveda-academy",
        "institution_type": InstitutionType.POLYTECHNIC,
        "ownership_type": OwnershipType.PRIVATE,
        "city": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "website_url": "https://vidyaveda.demo.example.com",
        "description": "Polytechnic and science academy providing industry-aligned diploma & degree programs.",
        "established_year": 2016,
        "number_of_students": 1100,
        "number_of_faculty": 50,
    },
    {
        "name": "NextGen Institute of Technology",
        "slug": "demo-fac-nextgen-institute-of-technology",
        "institution_type": InstitutionType.ENGINEERING,
        "ownership_type": OwnershipType.AUTONOMOUS,
        "city": "Secunderabad",
        "state": "Telangana",
        "website_url": "https://nextgen-tech.demo.example.com",
        "description": "Autonomous technology institute focusing on Artificial Intelligence and Data Science.",
        "established_year": 2009,
        "number_of_students": 3800,
        "number_of_faculty": 195,
    },
]

DEMO_FACULTY_INSTITUTION_NAMES = [inst["name"] for inst in FACULTY_INSTITUTIONS_DATA]

# Realistic Faculty Vacancies dataset
FACULTY_JOBS_DATA = [
    {
        "institution_index": 0,
        "title": "Assistant Professor – Computer Science",
        "slug": "demo-fac-job-asst-prof-cse",
        "vacancy_code": "FAC-VAC-2026-001",
        "department": "Computer Science & Engineering",
        "designation": Designation.ASSISTANT_PROFESSOR,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.PHD,
        "qualification_required": "M.Tech CSE / MCA / M.Sc Computer Science (PhD / NET / SET preferred)",
        "specialization_required": "Computer Science, Data Structures, Web Technologies",
        "experience_min": 2,
        "experience_max": 6,
        "salary_min": Decimal("500000.00"),
        "salary_max": Decimal("800000.00"),
        "vacancies": 3,
        "city": "Hyderabad",
        "description": "Seeking energetic Assistant Professor to teach undergraduate CSE courses and conduct lab sessions.",
    },
    {
        "institution_index": 1,
        "title": "Lecturer – Computer Applications (MCA)",
        "slug": "demo-fac-job-lecturer-mca",
        "vacancy_code": "FAC-VAC-2026-002",
        "department": "Computer Applications",
        "designation": Designation.LECTURER,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.MASTERS,
        "qualification_required": "MCA / M.Sc Computer Science (SET Qualified / 2+ years teaching exp preferred)",
        "specialization_required": "Database Systems, Software Engineering, Java",
        "experience_min": 1,
        "experience_max": 4,
        "salary_min": Decimal("400000.00"),
        "salary_max": Decimal("600000.00"),
        "vacancies": 2,
        "city": "Warangal",
        "description": "Lecturer role for handling MCA and B.Sc Computer Science theory and practical classes.",
    },
    {
        "institution_index": 2,
        "title": "Assistant Professor – Artificial Intelligence & Data Science",
        "slug": "demo-fac-job-asst-prof-aids",
        "vacancy_code": "FAC-VAC-2026-003",
        "department": "Artificial Intelligence & Machine Learning",
        "designation": Designation.ASSISTANT_PROFESSOR,
        "minimum_qualification": QualificationLevel.PHD,
        "preferred_qualification": QualificationLevel.PHD,
        "qualification_required": "PhD / M.Tech in AI/ML/Data Science (SCI journal publications preferred)",
        "specialization_required": "Machine Learning, Deep Learning, Python Programming",
        "experience_min": 4,
        "experience_max": 10,
        "salary_min": Decimal("800000.00"),
        "salary_max": Decimal("1300000.00"),
        "vacancies": 2,
        "city": "Hyderabad",
        "description": "Faculty vacancy for handling advanced AI/ML courses and mentoring research projects.",
    },
    {
        "institution_index": 3,
        "title": "Assistant Professor – Master of Business Administration (MBA)",
        "slug": "demo-fac-job-asst-prof-mba",
        "vacancy_code": "FAC-VAC-2026-004",
        "department": "Department of Management Studies",
        "designation": Designation.ASSISTANT_PROFESSOR,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.PHD,
        "qualification_required": "MBA (Finance / HR / Marketing) (NET / PhD preferred)",
        "specialization_required": "Corporate Finance, HR Analytics, Strategic Management",
        "experience_min": 3,
        "experience_max": 8,
        "salary_min": Decimal("600000.00"),
        "salary_max": Decimal("1000000.00"),
        "vacancies": 2,
        "city": "Hyderabad",
        "description": "Responsible for teaching MBA students, guiding industry internships, and conducting MDPs.",
    },
    {
        "institution_index": 4,
        "title": "Lecturer – Mathematics",
        "slug": "demo-fac-job-lecturer-maths",
        "vacancy_code": "FAC-VAC-2026-005",
        "department": "Department of Mathematics",
        "designation": Designation.LECTURER,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.MASTERS,
        "qualification_required": "M.Sc Mathematics / Applied Mathematics (CSIR-NET / SET preferred)",
        "specialization_required": "Calculus, Differential Equations, Discrete Math",
        "experience_min": 1,
        "experience_max": 5,
        "salary_min": Decimal("420000.00"),
        "salary_max": Decimal("650000.00"),
        "vacancies": 2,
        "city": "Nizamabad",
        "description": "Lecturer position for handling Engineering Mathematics and M.Sc Mathematics courses.",
    },
    {
        "institution_index": 5,
        "title": "Assistant Professor – English Literature & Communication",
        "slug": "demo-fac-job-asst-prof-english",
        "vacancy_code": "FAC-VAC-2026-006",
        "department": "Humanities & Sciences",
        "designation": Designation.ASSISTANT_PROFESSOR,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.PHD,
        "qualification_required": "M.A English / M.Phil (UGC-NET / SET / PhD preferred)",
        "specialization_required": "Soft Skills, Technical English, Phonetics & Communication",
        "experience_min": 2,
        "experience_max": 6,
        "salary_min": Decimal("480000.00"),
        "salary_max": Decimal("720000.00"),
        "vacancies": 1,
        "city": "Karimnagar",
        "description": "Faculty position for conducting Soft Skills lab and Technical English for engineering students.",
    },
    {
        "institution_index": 6,
        "title": "Computer Science Lecturer",
        "slug": "demo-fac-job-cs-lecturer",
        "vacancy_code": "FAC-VAC-2026-007",
        "department": "Computer Science",
        "designation": Designation.LECTURER,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.MASTERS,
        "qualification_required": "MCA / M.Sc CS / M.Tech (Teaching exp preferred)",
        "specialization_required": "C, C++, Data Structures, OS",
        "experience_min": 1,
        "experience_max": 3,
        "salary_min": Decimal("380000.00"),
        "salary_max": Decimal("550000.00"),
        "vacancies": 2,
        "city": "Khammam",
        "description": "Teaching undergraduate students programming fundamentals and operating systems.",
    },
    {
        "institution_index": 7,
        "title": "Assistant Professor – Data Analytics & Commerce",
        "slug": "demo-fac-job-asst-prof-commerce",
        "vacancy_code": "FAC-VAC-2026-008",
        "department": "Department of Commerce",
        "designation": Designation.ASSISTANT_PROFESSOR,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.MASTERS,
        "qualification_required": "M.Com / MBA (NET / SET / Tally / Excel cert preferred)",
        "specialization_required": "Financial Accounting, Business Analytics, Taxation",
        "experience_min": 2,
        "experience_max": 5,
        "salary_min": Decimal("450000.00"),
        "salary_max": Decimal("700000.00"),
        "vacancies": 2,
        "city": "Vijayawada",
        "description": "Handling B.Com (Computer Applications) and M.Com lectures and practical accounting labs.",
    },
    {
        "institution_index": 8,
        "title": "Lecturer – Physics & Electronics",
        "slug": "demo-fac-job-lecturer-physics",
        "vacancy_code": "FAC-VAC-2026-009",
        "department": "Physics & Electronics",
        "designation": Designation.LECTURER,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.MASTERS,
        "qualification_required": "M.Sc Physics (SET / B.Ed preferred)",
        "specialization_required": "Applied Physics, Digital Electronics, Semiconductor Physics",
        "experience_min": 1,
        "experience_max": 4,
        "salary_min": Decimal("360000.00"),
        "salary_max": Decimal("520000.00"),
        "vacancies": 1,
        "city": "Visakhapatnam",
        "description": "Conducting physics theory lectures and laboratory experiments for degree students.",
    },
    {
        "institution_index": 9,
        "title": "Assistant Professor – Computer Science & Engineering",
        "slug": "demo-fac-job-asst-prof-cse-nextgen",
        "vacancy_code": "FAC-VAC-2026-010",
        "department": "Computer Science & Engineering",
        "designation": Designation.ASSISTANT_PROFESSOR,
        "minimum_qualification": QualificationLevel.MASTERS,
        "preferred_qualification": QualificationLevel.PHD,
        "qualification_required": "M.Tech CSE / MCA (GATE/NET / PhD pursuing preferred)",
        "specialization_required": "Cloud Infrastructure, DevOps, Web Systems",
        "experience_min": 3,
        "experience_max": 7,
        "salary_min": Decimal("600000.00"),
        "salary_max": Decimal("950000.00"),
        "vacancies": 3,
        "city": "Secunderabad",
        "description": "Autonomous college faculty vacancy for teaching cloud computing and full-stack software development.",
    },
]


class Command(BaseCommand):
    help = "Generates realistic, deterministic demo data for the Faculty domain only in EduNaukari."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default=DEMO_PASSWORD,
            help="Default password for all demo accounts.",
        )

    def handle(self, *args, **options):
        password = options.get("password", DEMO_PASSWORD)

        self.stdout.write(self.style.WARNING("Starting Faculty Domain Demo Data Seeding..."))

        # Seed random for determinism
        random.seed(101)

        now = timezone.now()

        with transaction.atomic():
            # 1. Create StoredFile placeholder for resumes/CVs
            import uuid
            dummy_uuid = uuid.UUID("00000000-0000-0000-0000-000000000002")

            cv_file, _ = StoredFile.all_objects.get_or_create(
                original_filename="Faculty_Academic_CV.pdf",
                defaults={
                    "stored_filename": "faculty_demo_candidate_resume_hash.pdf",
                    "storage_backend": StorageBackendType.LOCAL,
                    "storage_path": "demo/resumes/faculty_sample_resume.pdf",
                    "file_type": StorageFileType.CV,
                    "file_size_bytes": 245000,
                    "mime_type": "application/pdf",
                    "domain": DomainType.FACULTY,
                    "owner_type": "professor",
                    "owner_id": dummy_uuid,
                    "uploaded_by_id": dummy_uuid,
                },
            )

            if cv_file.is_deleted:
                cv_file.is_deleted = False
                cv_file.deleted_at = None
                cv_file.save()

            # 2. Create 10 Faculty Job Seekers (ProfessorUser + ProfessorProfile)
            self.stdout.write("Creating 10 Faculty Job Seekers...")
            candidates = []
            candidate_profiles = []

            for data in FACULTY_CANDIDATES_DATA:
                email = data["email"]
                user, created = ProfessorUser.all_objects.get_or_create(
                    email=email,
                    defaults={
                        "is_active": True,
                        "email_verified": True,
                    },
                )
                user.set_password(password)
                user.is_active = True
                user.email_verified = True
                user.is_deleted = False
                user.deleted_at = None
                user.save()

                profile, _ = ProfessorProfile.all_objects.get_or_create(
                    user=user,
                    defaults={
                        "first_name": data["first_name"],
                        "last_name": data["last_name"],
                        "phone": data["phone"],
                        "highest_qualification": data["highest_qualification"],
                        "specialization": data["specialization"],
                        "research_interests": data["research_interests"],
                        "experience_years": data["experience_years"],
                        "teaching_experience_years": data["teaching_experience_years"],
                        "industry_experience_years": data["industry_experience_years"],
                        "publications_count": data["publications_count"],
                        "current_designation": data["current_designation"],
                        "current_institution": data["current_institution"],
                        "expected_salary": data["expected_salary"],
                        "preferred_locations": data["preferred_locations"],
                        "cv_file": cv_file,
                        "profile_completeness": 100,
                        "profile_completed": True,
                        "profile_status": "active",
                        "profile_visibility": "public",
                    },
                )
                # Ensure updated profile fields and soft-delete restoration
                profile.first_name = data["first_name"]
                profile.last_name = data["last_name"]
                profile.phone = data["phone"]
                profile.highest_qualification = data["highest_qualification"]
                profile.specialization = data["specialization"]
                profile.experience_years = data["experience_years"]
                profile.teaching_experience_years = data["teaching_experience_years"]
                profile.cv_file = cv_file
                profile.is_deleted = False
                profile.deleted_at = None
                profile.save()

                candidates.append(user)
                candidate_profiles.append(profile)

            # 3. Create 10 Fictional Educational Institutions & 10 Faculty Recruiters
            self.stdout.write("Creating 10 Educational Institutions & 10 Recruiter accounts...")
            recruiters = []
            colleges = []

            for idx, inst_data in enumerate(FACULTY_INSTITUTIONS_DATA):
                rec_data = FACULTY_RECRUITERS_DATA[idx]

                college, _ = College.all_objects.update_or_create(
                    slug=inst_data["slug"],
                    defaults={
                        "name": inst_data["name"],
                        "institution_type": inst_data["institution_type"],
                        "ownership_type": inst_data["ownership_type"],
                        "city": inst_data["city"],
                        "state": inst_data["state"],
                        "country": "India",
                        "website_url": inst_data["website_url"],
                        "description": inst_data["description"],
                        "established_year": inst_data["established_year"],
                        "number_of_students": inst_data["number_of_students"],
                        "number_of_faculty": inst_data["number_of_faculty"],
                        "is_active": True,
                        "profile_status": "active",
                        "profile_visibility": "public",
                        "profile_completeness": 100,
                        "profile_completed": True,
                        "is_deleted": False,
                        "deleted_at": None,
                    },
                )
                if college.is_deleted or not college.is_active:
                    college.is_deleted = False
                    college.deleted_at = None
                    college.is_active = True
                    college.save()

                rec_user, _ = CollegeUser.all_objects.get_or_create(
                    email=rec_data["email"],
                    defaults={
                        "is_active": True,
                        "email_verified": True,
                    },
                )
                rec_user.set_password(password)
                rec_user.is_active = True
                rec_user.email_verified = True
                rec_user.is_deleted = False
                rec_user.deleted_at = None
                rec_user.save()

                cm, _ = CollegeMember.all_objects.get_or_create(
                    college=college,
                    college_user=rec_user,
                    defaults={
                        "role": CollegeMemberRole.ADMIN,
                        "is_primary": True,
                        "is_active": True,
                    },
                )
                if cm.is_deleted or not cm.is_active:
                    cm.is_deleted = False
                    cm.deleted_at = None
                    cm.is_active = True
                    cm.save()

                recruiters.append(rec_user)
                colleges.append(college)

            # 4. Create 10 Faculty Job Posts (FacultyVacancy)
            self.stdout.write("Creating 10 Faculty Job Postings...")
            jobs = []
            for job_data in FACULTY_JOBS_DATA:
                college = colleges[job_data["institution_index"]]
                recruiter = recruiters[job_data["institution_index"]]

                vacancy_defaults = {
                    "college": college,
                    "posted_by": recruiter,
                    "title": job_data["title"],
                    "vacancy_code": job_data["vacancy_code"],
                    "department": job_data["department"],
                    "designation": job_data["designation"],
                    "minimum_qualification": job_data["minimum_qualification"],
                    "preferred_qualification": job_data["preferred_qualification"],
                    "qualification_required": job_data["qualification_required"],
                    "specialization_required": job_data["specialization_required"],
                    "experience_min": job_data["experience_min"],
                    "experience_max": job_data["experience_max"],
                    "salary_min": job_data["salary_min"],
                    "salary_max": job_data["salary_max"],
                    "salary_currency": "INR",
                    "vacancy_count": job_data["vacancies"],
                    "employment_type": "full_time",
                    "work_type": "onsite",
                    "city": job_data["city"],
                    "state": college.state,
                    "country": "India",
                    "description": job_data["description"],
                    "status": VacancyStatus.PUBLISHED,
                    "published_at": now - timedelta(days=random.randint(25, 60)),
                    "college_name_snapshot": college.name,
                }

                self._validate_model_values(FacultyVacancy, vacancy_defaults, context_label=job_data["slug"])

                vacancy, _ = FacultyVacancy.all_objects.get_or_create(
                    slug=job_data["slug"],
                    defaults=vacancy_defaults,
                )
                if vacancy.is_deleted or vacancy.status != VacancyStatus.PUBLISHED:
                    vacancy.is_deleted = False
                    vacancy.deleted_at = None
                    vacancy.status = VacancyStatus.PUBLISHED
                    vacancy.save()

                jobs.append(vacancy)

            # 5. Create 38–42 Job Applications across pipelines
            self.stdout.write("Creating Applications & Pipeline Workflows...")

            # Define application matrix mapping candidates to jobs logically
            # We will create 38 distinct applications
            application_map = [
                # (Candidate Index, Job Index, Status, Days Ago Applied)
                # Job 0: Asst Prof CSE (Veda Institute)
                (0, 0, FacultyApplicationStatus.JOINED, 55),       # Sai Krishna Reddy
                (1, 0, FacultyApplicationStatus.SHORTLISTED, 40),   # Sravani Goud
                (2, 0, FacultyApplicationStatus.SELECTED, 35),      # Venkatesh Rao
                (6, 0, FacultyApplicationStatus.JOINED, 55),       # Praveen Naidu -> ABSCONDED SCENARIO A
                (9, 0, FacultyApplicationStatus.REJECTED, 45),     # Karthik Varma
                # Job 1: Lecturer MCA (Sree Akshara College)
                (1, 1, FacultyApplicationStatus.JOINED, 50),       # Sravani Goud
                (6, 1, FacultyApplicationStatus.SHORTLISTED, 35),   # Praveen Naidu
                (0, 1, FacultyApplicationStatus.UNDER_REVIEW, 20),  # Sai Krishna
                (4, 1, FacultyApplicationStatus.WITHDRAWN, 25),     # Naveen Kumar
                # Job 2: Asst Prof AI & DS (ManaTech Engineering)
                (2, 2, FacultyApplicationStatus.JOINED, 60),       # Venkatesh Rao
                (0, 2, FacultyApplicationStatus.INTERVIEW_COMPLETED, 25), # Sai Krishna
                (1, 2, FacultyApplicationStatus.INTERVIEW_SCHEDULED, 15), # Sravani Goud
                (6, 2, FacultyApplicationStatus.APPLIED, 10),       # Praveen Naidu
                # Job 3: Asst Prof MBA (BlueSky School of Management)
                (5, 3, FacultyApplicationStatus.JOINING_IN_PROGRESS, 30), # Keerthana Reddy
                (7, 3, FacultyApplicationStatus.JOINED, 85),       # Divya Sri -> ABSCONDED SCENARIO B
                (9, 3, FacultyApplicationStatus.SHORTLISTED, 25),   # Karthik Varma
                (3, 3, FacultyApplicationStatus.REJECTED, 40),     # Harika Devi
                # Job 4: Lecturer Mathematics (Pragathi PG College)
                (4, 4, FacultyApplicationStatus.JOINED, 45),       # Naveen Kumar
                (8, 4, FacultyApplicationStatus.INTERVIEW_COMPLETED, 20), # Anusha Reddy
                (0, 4, FacultyApplicationStatus.APPLIED, 8),        # Sai Krishna
                # Job 5: Asst Prof English (Nova Institute of Sciences)
                (3, 5, FacultyApplicationStatus.JOINED, 50),       # Harika Devi
                (5, 5, FacultyApplicationStatus.SHORTLISTED, 30),   # Keerthana Reddy
                (8, 5, FacultyApplicationStatus.UNDER_REVIEW, 18),  # Anusha Reddy
                # Job 6: Computer Science Lecturer (Arya College of Engineering)
                (6, 6, FacultyApplicationStatus.INTERVIEW_SCHEDULED, 14), # Praveen Naidu
                (1, 6, FacultyApplicationStatus.SHORTLISTED, 22),   # Sravani Goud
                (0, 6, FacultyApplicationStatus.APPLIED, 5),        # Sai Krishna
                (9, 6, FacultyApplicationStatus.REJECTED, 30),     # Karthik Varma
                # Job 7: Asst Prof Commerce (Sahasra Degree & PG)
                (9, 7, FacultyApplicationStatus.JOINED, 48),       # Karthik Varma
                (5, 7, FacultyApplicationStatus.INTERVIEW_COMPLETED, 22), # Keerthana
                (7, 7, FacultyApplicationStatus.WITHDRAWN, 35),     # Divya Sri
                (3, 7, FacultyApplicationStatus.UNDER_REVIEW, 12),  # Harika Devi
                # Job 8: Lecturer Physics (VidyaVeda Academy)
                (8, 8, FacultyApplicationStatus.JOINED, 40),       # Anusha Reddy
                (4, 8, FacultyApplicationStatus.SHORTLISTED, 20),   # Naveen Kumar
                (2, 8, FacultyApplicationStatus.APPLIED, 6),        # Venkatesh Rao
                # Job 9: Asst Prof CSE (NextGen Institute of Technology)
                (0, 9, FacultyApplicationStatus.JOINING_IN_PROGRESS, 28), # Sai Krishna
                (2, 9, FacultyApplicationStatus.SHORTLISTED, 18),   # Venkatesh Rao
                (6, 9, FacultyApplicationStatus.UNDER_REVIEW, 15),  # Praveen Naidu
                (1, 9, FacultyApplicationStatus.APPLIED, 4),        # Sravani Goud
            ]

            created_applications = []
            app_stats = {
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

            for candidate_idx, job_idx, status, applied_days_ago in application_map:
                cand_profile = candidate_profiles[candidate_idx]
                job = jobs[job_idx]
                college = job.college
                applied_date = now - timedelta(days=applied_days_ago)

                app, _ = FacultyApplication.all_objects.get_or_create(
                    vacancy=job,
                    professor=cand_profile,
                    defaults={
                        "college": college,
                        "cv_file": cv_file,
                        "status": status,
                        "applied_at": applied_date,
                        "status_changed_at": applied_date,
                        "source": ApplicationSource.DIRECT,
                        "department": job.department,
                        "expected_salary": cand_profile.expected_salary,
                        "current_institution": cand_profile.current_institution,
                        "current_designation": cand_profile.current_designation,
                        "research_publications_count": cand_profile.publications_count,
                        "applicant_name_snapshot": f"{cand_profile.first_name} {cand_profile.last_name}",
                        "vacancy_title_snapshot": job.title,
                        "college_name_snapshot": college.name,
                    },
                )
                if app.is_deleted:
                    app.is_deleted = False
                    app.deleted_at = None
                app.status = status
                app.applied_at = applied_date
                app.save()

                created_applications.append(app)

                # Record status history
                FacultyApplicationStatusHistory.objects.get_or_create(
                    application=app,
                    from_status="",
                    to_status=FacultyApplicationStatus.APPLIED,
                    defaults={
                        "changed_at": applied_date,
                        "changed_by_id": cand_profile.user.pk,
                        "changed_by_domain": DomainType.FACULTY,
                        "notes": "Application submitted by candidate",
                    },
                )

                if status != FacultyApplicationStatus.APPLIED:
                    history_date = applied_date + timedelta(days=random.randint(2, 7))
                    FacultyApplicationStatusHistory.objects.get_or_create(
                        application=app,
                        from_status=FacultyApplicationStatus.APPLIED,
                        to_status=status,
                        defaults={
                            "changed_at": history_date,
                            "changed_by_id": job.posted_by.pk,
                            "changed_by_domain": DomainType.FACULTY,
                            "notes": f"Status changed to {status}",
                        },
                    )

                FacultyApplicationTimelineEvent.objects.get_or_create(
                    application=app,
                    event_type=TimelineEventType.STATUS_CHANGED,
                    from_status=FacultyApplicationStatus.APPLIED if status != FacultyApplicationStatus.APPLIED else "",
                    to_status=status,
                    defaults={
                        "actor_id": cand_profile.user.pk,
                        "actor_domain": DomainType.FACULTY,
                        "notes": f"Candidate status moved to {status}",
                        "occurred_at": applied_date,
                    },
                )

                # Track counts
                app_stats["total_applications"] += 1
                if status == FacultyApplicationStatus.APPLIED:
                    app_stats["applied"] += 1
                elif status == FacultyApplicationStatus.UNDER_REVIEW:
                    app_stats["under_review"] += 1
                elif status == FacultyApplicationStatus.SHORTLISTED:
                    app_stats["shortlisted"] += 1
                elif status in [FacultyApplicationStatus.INTERVIEW_SCHEDULED, FacultyApplicationStatus.INTERVIEW_COMPLETED]:
                    app_stats["interviews"] += 1
                elif status == FacultyApplicationStatus.SELECTED:
                    app_stats["selected"] += 1
                elif status in [FacultyApplicationStatus.JOINED, FacultyApplicationStatus.JOINING_IN_PROGRESS]:
                    app_stats["joined"] += 1
                elif status == FacultyApplicationStatus.REJECTED:
                    app_stats["rejected"] += 1
                elif status == FacultyApplicationStatus.WITHDRAWN:
                    app_stats["withdrawn"] += 1

            # 6. Teaching Demo & Interview Evaluations
            self.stdout.write("Creating Teaching Demo & Interview Evaluation records...")
            demo_topics = [
                "DBMS Normalization & Relational Architecture",
                "Introduction to Machine Learning Algorithms",
                "Differential Equations and Linear Algebra",
                "Business Communication & Soft Skills in Academia",
                "Data Structures: Trees, Graphs and Searching",
                "Corporate Finance & Portfolio Management",
            ]

            eval_count = 0
            for app in created_applications:
                if app.status in [
                    FacultyApplicationStatus.INTERVIEW_COMPLETED,
                    FacultyApplicationStatus.SELECTED,
                    FacultyApplicationStatus.JOINING_IN_PROGRESS,
                    FacultyApplicationStatus.JOINED,
                ]:
                    topic = demo_topics[eval_count % len(demo_topics)]
                    InterviewEvaluation.objects.get_or_create(
                        domain=DomainType.FACULTY,
                        application_id=app.pk,
                        defaults={
                            "teaching_skills": 4,
                            "subject_knowledge": 5,
                            "communication_rating": 4,
                            "technical_rating": 4,
                            "culture_fit": 4,
                            "overall_rating": 4,
                            "recommendation": "select",
                            "interview_notes": f"Teaching demo on '{topic}'. Excellent blackboard delivery, student engagement, and subject clarity.",
                        },
                    )
                    eval_count += 1

            # 7. Fee Schedules & Billing Foundation
            fee_schedule, _ = FeeSchedule.all_objects.get_or_create(
                domain=DomainType.FACULTY,
                fee_type=FeeType.FIXED,
                defaults={
                    "name": "Standard Faculty Placement Fee",
                    "fixed_amount": Decimal("25000.00"),
                    "percentage_rate": Decimal("0.00"),
                    "is_active": True,
                },
            )

            # 8. ABSCONDED & 90-DAY GUARANTEE CLAIM SCENARIOS

            # SCENARIO A: PENDING REFUND CLAIM (Praveen Naidu - Candidate 07 @ Veda Institute - Job 0)
            self.stdout.write("Creating Absconded Candidate Scenario A (Pending Claim)...")
            app_scenario_a = FacultyApplication.all_objects.get(
                professor__user__email="faculty.candidate07.praveen@example.com",
                vacancy__slug="demo-fac-job-asst-prof-cse",
            )
            if app_scenario_a.is_deleted:
                app_scenario_a.is_deleted = False
                app_scenario_a.deleted_at = None
            # Timestamps for Scenario A
            applied_a = now - timedelta(days=55)
            selected_a = now - timedelta(days=40)
            joined_a = now - timedelta(days=34)
            exit_a = now - timedelta(days=12)
            claim_a = now - timedelta(days=10)

            app_scenario_a.status = FacultyApplicationStatus.JOINED
            app_scenario_a.joined_at = joined_a
            app_scenario_a.placed_at = selected_a
            app_scenario_a.save()

            PlacementDetails.objects.get_or_create(
                domain=DomainType.FACULTY,
                application_id=app_scenario_a.pk,
                defaults={
                    "selected_at": selected_a,
                    "expected_joining_date": joined_a.date(),
                    "actual_joining_date": joined_a.date(),
                    "agreed_salary": Decimal("500000.00"),
                    "employee_id": "EMP-FAC-2026-007",
                },
            )

            inv_a, _ = Invoice.all_objects.update_or_create(
                invoice_number="INV-DEMO-FAC-001",
                defaults={
                    "domain": DomainType.FACULTY,
                    "placement_fee_id": app_scenario_a.pk,
                    "bill_to_entity_type": EntityReferenceType.FACULTY_COLLEGE,
                    "bill_to_entity_id": app_scenario_a.college.pk,
                    "subtotal": Decimal("25000.00"),
                    "tax_amount": Decimal("4500.00"),
                    "total_amount": Decimal("29500.00"),
                    "amount_paid": Decimal("29500.00"),
                    "status": "paid",
                    "paid_at": joined_a + timedelta(days=2),
                },
            )
            if inv_a.is_deleted:
                inv_a.is_deleted = False
                inv_a.deleted_at = None
                inv_a.save()

            guarantee_a, _ = PlacementGuarantee.all_objects.update_or_create(
                domain=DomainType.FACULTY,
                application_entity_type=EntityReferenceType.FACULTY_APPLICATION,
                application_entity_id=app_scenario_a.pk,
                defaults={
                    "invoice_id": inv_a.pk,
                    "placement_fee_id": app_scenario_a.pk,
                    "guarantee_days": 90,
                    "starts_at": joined_a,
                    "expires_at": joined_a + timedelta(days=90),
                    "status": GuaranteeStatus.CLAIMED,
                },
            )
            if guarantee_a.is_deleted:
                guarantee_a.is_deleted = False
                guarantee_a.deleted_at = None
                guarantee_a.save()

            claim_obj_a, _ = GuaranteeClaim.all_objects.update_or_create(
                claim_number="CLM-DEMO-FAC-001",
                defaults={
                    "domain": DomainType.FACULTY,
                    "recruiter_id": app_scenario_a.vacancy.posted_by.pk,
                    "institution_id": app_scenario_a.college.pk,
                    "guarantee_id": guarantee_a.pk,
                    "application_entity_type": "facultyapplication",
                    "application_entity_id": app_scenario_a.pk,
                    "placement_fee_id": app_scenario_a.pk,
                    "invoice_id": inv_a.pk,
                    "joining_date": joined_a.date(),
                    "guarantee_start_date": joined_a.date(),
                    "guarantee_end_date": (joined_a + timedelta(days=90)).date(),
                    "exit_date": exit_a.date(),
                    "exit_reason": ExitReason.ABSCONDED,
                    "claim_type": ClaimType.REFUND,
                    "status": ClaimStatus.SUBMITTED,
                    "refund_amount": Decimal("29500.00"),
                    "submitted_at": claim_a,
                    "reason": "Faculty member absconded without notice after 22 days of joining.",
                    "claim_description": "Candidate Praveen Naidu stopped attending lectures from 12 days ago without formal resignation during 90-day guarantee period.",
                },
            )
            if claim_obj_a.is_deleted:
                claim_obj_a.is_deleted = False
                claim_obj_a.deleted_at = None
                claim_obj_a.save()

            GuaranteeClaimHistory.objects.get_or_create(
                claim=claim_obj_a,
                from_status=ClaimStatus.DRAFT,
                to_status=ClaimStatus.SUBMITTED,
                defaults={
                    "changed_by_id": app_scenario_a.vacancy.posted_by.pk,
                    "notes": "Claim submitted by Veda Institute HR for candidate early exit.",
                    "changed_at": claim_a,
                },
            )

            # SCENARIO B: APPROVED REFUND CLAIM (Divya Sri - Candidate 08 @ BlueSky School of Management - Job 3)
            self.stdout.write("Creating Absconded Candidate Scenario B (Approved Claim)...")
            app_scenario_b = FacultyApplication.all_objects.get(
                professor__user__email="faculty.candidate08.divyasri@example.com",
                vacancy__slug="demo-fac-job-asst-prof-mba",
            )
            if app_scenario_b.is_deleted:
                app_scenario_b.is_deleted = False
                app_scenario_b.deleted_at = None
            applied_b = now - timedelta(days=85)
            selected_b = now - timedelta(days=78)
            joined_b = now - timedelta(days=75)
            exit_b = now - timedelta(days=30)
            claim_b = now - timedelta(days=28)
            approval_b = now - timedelta(days=20)

            app_scenario_b.status = FacultyApplicationStatus.JOINED
            app_scenario_b.joined_at = joined_b
            app_scenario_b.placed_at = selected_b
            app_scenario_b.save()

            PlacementDetails.objects.get_or_create(
                domain=DomainType.FACULTY,
                application_id=app_scenario_b.pk,
                defaults={
                    "selected_at": selected_b,
                    "expected_joining_date": joined_b.date(),
                    "actual_joining_date": joined_b.date(),
                    "agreed_salary": Decimal("900000.00"),
                    "employee_id": "EMP-FAC-2026-008",
                },
            )

            inv_b, _ = Invoice.all_objects.update_or_create(
                invoice_number="INV-DEMO-FAC-002",
                defaults={
                    "domain": DomainType.FACULTY,
                    "placement_fee_id": app_scenario_b.pk,
                    "bill_to_entity_type": EntityReferenceType.FACULTY_COLLEGE,
                    "bill_to_entity_id": app_scenario_b.college.pk,
                    "subtotal": Decimal("25000.00"),
                    "tax_amount": Decimal("4500.00"),
                    "total_amount": Decimal("29500.00"),
                    "amount_paid": Decimal("29500.00"),
                    "status": "paid",
                    "paid_at": joined_b + timedelta(days=3),
                },
            )
            if inv_b.is_deleted:
                inv_b.is_deleted = False
                inv_b.deleted_at = None
                inv_b.save()

            guarantee_b, _ = PlacementGuarantee.all_objects.update_or_create(
                domain=DomainType.FACULTY,
                application_entity_type=EntityReferenceType.FACULTY_APPLICATION,
                application_entity_id=app_scenario_b.pk,
                defaults={
                    "invoice_id": inv_b.pk,
                    "placement_fee_id": app_scenario_b.pk,
                    "guarantee_days": 90,
                    "starts_at": joined_b,
                    "expires_at": joined_b + timedelta(days=90),
                    "status": GuaranteeStatus.CLAIMED,
                },
            )
            if guarantee_b.is_deleted:
                guarantee_b.is_deleted = False
                guarantee_b.deleted_at = None
                guarantee_b.save()

            claim_obj_b, _ = GuaranteeClaim.all_objects.update_or_create(
                claim_number="CLM-DEMO-FAC-002",
                defaults={
                    "domain": DomainType.FACULTY,
                    "recruiter_id": app_scenario_b.vacancy.posted_by.pk,
                    "institution_id": app_scenario_b.college.pk,
                    "guarantee_id": guarantee_b.pk,
                    "application_entity_type": "facultyapplication",
                    "application_entity_id": app_scenario_b.pk,
                    "placement_fee_id": app_scenario_b.pk,
                    "invoice_id": inv_b.pk,
                    "joining_date": joined_b.date(),
                    "guarantee_start_date": joined_b.date(),
                    "guarantee_end_date": (joined_b + timedelta(days=90)).date(),
                    "exit_date": exit_b.date(),
                    "exit_reason": ExitReason.ABSCONDED,
                    "claim_type": ClaimType.REFUND,
                    "status": ClaimStatus.APPROVED,
                    "refund_amount": Decimal("29500.00"),
                    "submitted_at": claim_b,
                    "reviewed_at": approval_b,
                    "resolved_at": approval_b,
                    "approval_date": approval_b.date(),
                    "reason": "Faculty member absconded within 45 days of joining.",
                    "claim_description": "Dr. Divya Sri discontinued teaching duties at BlueSky School of Management during guarantee period.",
                    "resolution_notes": "Claim verified against attendance records. Full refund approved per 90-day recruitment guarantee policy.",
                },
            )
            if claim_obj_b.is_deleted:
                claim_obj_b.is_deleted = False
                claim_obj_b.deleted_at = None
                claim_obj_b.save()

            GuaranteeClaimHistory.objects.get_or_create(
                claim=claim_obj_b,
                from_status=ClaimStatus.SUBMITTED,
                to_status=ClaimStatus.APPROVED,
                defaults={
                    "changed_by_id": app_scenario_b.vacancy.posted_by.pk,
                    "notes": "Claim reviewed and approved by Platform Operations Admin.",
                    "changed_at": approval_b,
                },
            )

            app_stats["absconded"] = 2
            app_stats["claims"] = 2

            # 9. Invariant Validation
            self._validate_invariants()

            # 10. Print Summary Dashboard
            self._print_summary_dashboard(candidates, recruiters, colleges, jobs, app_stats)

    def _validate_model_values(self, model, values_dict, context_label=""):
        """Pre-flight schema validation checking max_length, choice keys, and nullability."""
        errors = []
        field_map = {f.name: f for f in model._meta.fields}

        for key, value in values_dict.items():
            if key not in field_map or value is None:
                continue

            field = field_map[key]

            max_length = getattr(field, "max_length", None)
            if max_length and isinstance(value, str) and len(value) > max_length:
                errors.append(
                    f"[{context_label}] {model.__name__}.{key}: {len(value)} chars exceeds max_length={max_length}: {value!r}"
                )

            if field.choices:
                valid_keys = [choice[0] for choice in field.choices]
                if value not in valid_keys:
                    errors.append(
                        f"[{context_label}] {model.__name__}.{key}: {value!r} is not a valid choice key. Expected one of: {valid_keys}"
                    )

        if errors:
            raise ValueError(f"Pre-flight demo data schema validation failed:\n" + "\n".join(errors))

    def _validate_invariants(self):
        """Validates critical business logic and relationship invariants for demo data."""
        self.stdout.write("Validating demo data invariants...")

        seeker_count = ProfessorProfile.objects.filter(user__email__startswith="faculty.candidate").count()
        if seeker_count != 10:
            raise ValueError(f"Expected 10 Faculty Job Seekers, found {seeker_count}")

        recruiter_count = CollegeUser.objects.filter(email__startswith="faculty.recruiter").count()
        if recruiter_count != 10:
            raise ValueError(f"Expected 10 Faculty Recruiters, found {recruiter_count}")

        college_count = College.objects.filter(name__in=DEMO_FACULTY_INSTITUTION_NAMES).count()
        if college_count != 10:
            raise ValueError(f"Expected 10 Educational Institutions, found {college_count}")

        job_count = FacultyVacancy.objects.filter(college__name__in=DEMO_FACULTY_INSTITUTION_NAMES).count()
        if job_count != 10:
            raise ValueError(f"Expected 10 Faculty Jobs, found {job_count}")

        app_count = FacultyApplication.objects.filter(college__name__in=DEMO_FACULTY_INSTITUTION_NAMES).count()
        if app_count < 30:
            raise ValueError(f"Expected at least 30 Applications, found {app_count}")

        # Check Guarantee Claims
        claim_count = GuaranteeClaim.objects.filter(claim_number__startswith="CLM-DEMO-FAC").count()
        if claim_count < 2:
            raise ValueError(f"Expected 2 valid 90-day Guarantee Claim scenarios, found {claim_count}")

        # Assert no IT domain records were created by this script
        from apps.accounts.models import ITUser
        from apps.jobs.models import JobPosting
        if ITUser.objects.filter(email__startswith="faculty.candidate").exists():
            raise ValueError("IT domain records were illegally created in Faculty seeder!")

        self.stdout.write(self.style.SUCCESS("All invariants validated successfully!"))

    def _print_summary_dashboard(self, candidates, recruiters, colleges, jobs, stats):
        """Prints formatted ASCII dashboard summary of created Faculty demo dataset."""
        summary = f"""
=====================================================
EDUNAUKARI FACULTY DOMAIN DEMO DATA CREATED
=====================================================

Users & Profiles
  Faculty Job Seekers .......... {len(candidates)}
  Faculty Recruiters ........... {len(recruiters)}

Institutions
  Educational Institutions ..... {len(colleges)}

Recruitment Pipeline
  Faculty Jobs ................. {len(jobs)}
  Total Applications ........... {stats['total_applications']}
  Applied / Under Review ....... {stats['applied'] + stats['under_review']}
  Shortlisted .................. {stats['shortlisted']}
  Interviews & Demos ........... {stats['interviews']}
  Selected ..................... {stats['selected']}
  Joined / Placed .............. {stats['joined']}
  Rejected ..................... {stats['rejected']}
  Withdrawn .................... {stats['withdrawn']}
  Absconded Candidates ......... {stats['absconded']}

Guarantee & Refund Claims (90-Day Policy)
  Eligible Refund Claims ....... {stats['claims']}
  Pending Refund Claims ........ 1  (CLM-DEMO-FAC-001)
  Approved Refund Claims ....... 1  (CLM-DEMO-FAC-002)

Demo Account Password
  Password ..................... {DEMO_PASSWORD}

Sample Job Seeker Email
  faculty.candidate01.saikrishna@example.com

Sample Recruiter Email
  faculty.recruiter01.sirisha@example.com

=====================================================
"""
        self.stdout.write(summary)


if __name__ == "__main__":
    Command().handle()
