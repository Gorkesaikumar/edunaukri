import os
import shutil
from django.conf import settings
from .base_seeder import BaseSeeder
from apps.documents.models import StoredFile
from apps.documents.services.storage_service import StorageService
from apps.accounts.models import AdminUser


class FileAssetSeeder(BaseSeeder):
    def seed_assets(self):
        self.log("Seeding dummy file assets...")

        # Create a dummy pdf and png in a temp dir
        temp_dir = os.path.join(settings.BASE_DIR, "tmp_seed")
        os.makedirs(temp_dir, exist_ok=True)

        dummy_pdf_path = os.path.join(temp_dir, "dummy_resume.pdf")
        with open(dummy_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%Dummy PDF for Seeding\n")

        dummy_png_path = os.path.join(temp_dir, "dummy_logo.png")
        with open(dummy_png_path, "wb") as f:
            # minimal valid PNG
            f.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )

        # Create StoredFile instances
        storage_service = StorageService()

        # We need to simulate uploading these files using Django's file handling
        from django.core.files import File

        from apps.core.constants.enums import DomainType
        from apps.documents.constants.enums import StorageFileType

        # IT Seekers Resumes
        from apps.it_recruitment.models import JobSeekerProfile

        for profile in JobSeekerProfile.objects.all():
            with open(dummy_pdf_path, "rb") as f:
                django_file = File(f, name="resume.pdf")
                stored_file = storage_service.upload(
                    uploaded_file=django_file,
                    domain=DomainType.IT,
                    file_type=StorageFileType.RESUME,
                    owner_type="jobseeker",
                    owner_id=profile.id,
                    uploaded_by_id=profile.user.id,
                )
                profile.resume_file = stored_file
                profile.save()

        # Faculty Seekers CVs
        from apps.academic_recruitment.models import ProfessorProfile

        for profile in ProfessorProfile.objects.all():
            with open(dummy_pdf_path, "rb") as f:
                django_file = File(f, name="cv.pdf")
                stored_file = storage_service.upload(
                    uploaded_file=django_file,
                    domain=DomainType.FACULTY,
                    file_type=StorageFileType.CV,
                    owner_type="professor",
                    owner_id=profile.id,
                    uploaded_by_id=profile.user.id,
                )
                profile.cv_file = stored_file
                profile.save()

        # Company Logos
        from apps.companies.models import Company

        for company in Company.objects.all():
            with open(dummy_png_path, "rb") as f:
                django_file = File(f, name="logo.png")
                recruiter_user = (
                    company.members.first().recruiter.user
                    if company.members.exists()
                    else AdminUser.objects.first()
                )
                stored_file = storage_service.upload(
                    uploaded_file=django_file,
                    domain=DomainType.IT,
                    file_type=StorageFileType.COMPANY_LOGO,
                    owner_type="company",
                    owner_id=company.id,
                    uploaded_by_id=recruiter_user.id,
                )
                company.logo = stored_file
                company.save()

        # College Logos
        from apps.colleges.models import College

        for college in College.objects.all():
            with open(dummy_png_path, "rb") as f:
                django_file = File(f, name="college_logo.png")
                college_user = (
                    college.members.first().college_user
                    if college.members.exists()
                    else AdminUser.objects.first()
                )
                stored_file = storage_service.upload(
                    uploaded_file=django_file,
                    domain=DomainType.FACULTY,
                    file_type=StorageFileType.COLLEGE_LOGO,
                    owner_type="college",
                    owner_id=college.id,
                    uploaded_by_id=college_user.id,
                )
                college.logo = stored_file
                college.save()

        shutil.rmtree(temp_dir, ignore_errors=True)
        self.log("Dummy assets attached successfully.")

    def seed_all(self):
        self.seed_assets()
