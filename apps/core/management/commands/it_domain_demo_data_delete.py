import os
import sys
from django.core.management.base import BaseCommand
from django.db import transaction

# Initialize Django if executed standalone
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    import django
    django.setup()

from apps.accounts.models import ITUser
from apps.accounts.models.it_user_role import ITUserRole
from apps.companies.models import Company, CompanyMember, CompanyLocation
from apps.documents.models import StoredFile
from apps.guarantee_claims.models import GuaranteeClaim, GuaranteeClaimHistory, PlacementGuarantee
from apps.invoices.models import Invoice, InvoiceLineItem
from apps.billing.models import PlacementFee
from apps.it_recruitment.models import (
    JobSeekerProfile,
    RecruiterProfile,
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProject,
    JobSeekerCertification,
)
from apps.jobs.models import (
    JobPosting,
    JobPostingSkill,
    JobLocation,
    JobSeekerSkill,
    SavedJob,
)
from apps.applications.models import (
    JobApplication,
    JobApplicationStatusHistory,
    JobApplicationTimelineEvent,
    JobApplicationInterview,
    PlacementDetails,
    InterviewEvaluation,
)

DEMO_SEEKER_EMAILS = [
    "it.seeker01.saikiran@example.com",
    "it.seeker02.anusha@example.com",
    "it.seeker03.venkatesh@example.com",
    "it.seeker04.nikhila@example.com",
    "it.seeker05.arjun@example.com",
    "it.seeker06.swathi@example.com",
    "it.seeker07.karthik@example.com",
    "it.seeker08.harika@example.com",
    "it.seeker09.rahul@example.com",
    "it.seeker10.divyasri@example.com",
]

DEMO_RECRUITER_EMAILS = [
    "it.recruiter01.sravani@example.com",
    "it.recruiter02.saiteja@example.com",
    "it.recruiter03.manoj@example.com",
    "it.recruiter04.lakshmi@example.com",
    "it.recruiter05.rohit@example.com",
    "it.recruiter06.keerthana@example.com",
    "it.recruiter07.praveen@example.com",
    "it.recruiter08.deepika@example.com",
    "it.recruiter09.naveen@example.com",
    "it.recruiter10.sirisha@example.com",
]


class Command(BaseCommand):
    help = "Safely deletes ONLY the IT domain demo data created by it_domain_demo_data seeder."

    @staticmethod
    def _safe_delete(qs) -> int:
        """Safely performs deletion on queryset and returns affected count."""
        try:
            res = qs.delete()
            if isinstance(res, tuple) and len(res) > 0:
                return res[0]
            elif isinstance(res, int):
                return res
            return 0
        except Exception:
            return 0

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Clean Deletion of IT Domain Demo Data..."))

        # Find target demo users
        seeker_users = list(ITUser.all_objects.filter(email__in=DEMO_SEEKER_EMAILS))
        recruiter_users = list(ITUser.all_objects.filter(email__in=DEMO_RECRUITER_EMAILS))
        all_demo_user_ids = [u.pk for u in seeker_users + recruiter_users]

        # Find target demo profiles
        seeker_profiles = list(JobSeekerProfile.all_objects.filter(user_id__in=[u.pk for u in seeker_users]))
        recruiter_profiles = list(RecruiterProfile.all_objects.filter(user_id__in=[u.pk for u in recruiter_users]))
        seeker_profile_ids = [p.pk for p in seeker_profiles]
        recruiter_profile_ids = [p.pk for p in recruiter_profiles]

        # Find target demo companies
        companies = list(Company.all_objects.filter(name__startswith="[DEMO-IT]"))
        company_ids = [c.pk for c in companies]

        # Find target demo jobs
        jobs = list(JobPosting.all_objects.filter(company_id__in=company_ids))
        job_ids = [j.pk for j in jobs]

        # Find target demo applications
        applications = list(JobApplication.all_objects.filter(job_posting_id__in=job_ids))
        application_ids = [a.pk for a in applications]

        # 1. Delete Guarantee Claims & History
        claims = list(GuaranteeClaim.all_objects.filter(application_entity_id__in=application_ids))
        claim_ids = [c.pk for c in claims]
        history_count = self._safe_delete(GuaranteeClaimHistory.objects.filter(claim_id__in=claim_ids))
        claims_count = self._safe_delete(GuaranteeClaim.all_objects.filter(id__in=claim_ids))

        # 2. Delete Placement Guarantees
        guarantees_count = self._safe_delete(PlacementGuarantee.all_objects.filter(application_entity_id__in=application_ids))

        # 3. Delete Invoices & Line Items
        invoices = list(Invoice.all_objects.filter(placement_fee_id__in=application_ids))
        invoice_ids = [inv.pk for inv in invoices]
        line_items_count = self._safe_delete(InvoiceLineItem.all_objects.filter(invoice_id__in=invoice_ids))
        invoices_count = self._safe_delete(Invoice.all_objects.filter(id__in=invoice_ids))

        # 4. Delete Placement Fees
        placement_fees_count = self._safe_delete(PlacementFee.all_objects.filter(entity_id__in=application_ids))

        # 5. Delete Placement Details & Interview Evaluations & Interviews
        placement_details_count = self._safe_delete(PlacementDetails.all_objects.filter(application_id__in=application_ids))
        evaluations_count = self._safe_delete(InterviewEvaluation.all_objects.filter(application_id__in=application_ids))
        interviews_count = self._safe_delete(JobApplicationInterview.all_objects.filter(application_id__in=application_ids))

        # 6. Delete Application Status History & Timeline Events & Applications
        app_history_count = self._safe_delete(JobApplicationStatusHistory.objects.filter(application_id__in=application_ids))
        app_timeline_count = self._safe_delete(JobApplicationTimelineEvent.objects.filter(application_id__in=application_ids))
        applications_count = self._safe_delete(JobApplication.all_objects.filter(id__in=application_ids))

        # 7. Delete Saved Jobs, Job Posting Skills, Job Locations & Job Postings
        saved_jobs_count = self._safe_delete(SavedJob.all_objects.filter(job_posting_id__in=job_ids))
        job_skills_count = self._safe_delete(JobPostingSkill.all_objects.filter(job_posting_id__in=job_ids))
        job_locations_count = self._safe_delete(JobLocation.all_objects.filter(job_posting_id__in=job_ids))
        jobs_count = self._safe_delete(JobPosting.all_objects.filter(id__in=job_ids))

        # 8. Delete Company Members, Company Locations & Companies
        company_members_count = self._safe_delete(CompanyMember.all_objects.filter(company_id__in=company_ids))
        company_locations_count = self._safe_delete(CompanyLocation.all_objects.filter(company_id__in=company_ids))
        companies_count = self._safe_delete(Company.all_objects.filter(id__in=company_ids))

        # 9. Delete Job Seeker Skills, Educations, Experiences, Projects, Certifications & Profiles
        seeker_skills_count = self._safe_delete(JobSeekerSkill.all_objects.filter(job_seeker_id__in=seeker_profile_ids))
        seeker_edu_count = self._safe_delete(JobSeekerEducation.all_objects.filter(job_seeker_id__in=seeker_profile_ids))
        seeker_exp_count = self._safe_delete(JobSeekerExperience.all_objects.filter(job_seeker_id__in=seeker_profile_ids))
        seeker_proj_count = self._safe_delete(JobSeekerProject.all_objects.filter(job_seeker_id__in=seeker_profile_ids))
        seeker_cert_count = self._safe_delete(JobSeekerCertification.all_objects.filter(job_seeker_id__in=seeker_profile_ids))

        seeker_profiles_count = self._safe_delete(JobSeekerProfile.all_objects.filter(id__in=seeker_profile_ids))
        recruiter_profiles_count = self._safe_delete(RecruiterProfile.all_objects.filter(id__in=recruiter_profile_ids))

        # 10. Delete ITUser Roles & ITUsers
        user_roles_count = self._safe_delete(ITUserRole.objects.filter(user_id__in=all_demo_user_ids))
        users_count = self._safe_delete(ITUser.all_objects.filter(id__in=all_demo_user_ids))

        # 11. Delete Dummy Resume Stored Files
        stored_files_count = self._safe_delete(StoredFile.all_objects.filter(original_filename="it_demo_candidate_resume.pdf"))

        summary = f"""
====================================================
IT DOMAIN DEMO DATA DELETED
====================================================

Claims Deleted ............. {claims_count}
Claim History Deleted ...... {history_count}
Guarantees Deleted ......... {guarantees_count}
Invoices Deleted ........... {invoices_count}
Placement Details Deleted .. {placement_details_count}
Interviews Deleted ......... {interviews_count}
Applications Deleted ....... {applications_count}
Jobs Deleted ............... {jobs_count}
Companies Deleted .......... {companies_count}
Recruiter Profiles Deleted . {recruiter_profiles_count}
Job Seeker Profiles Deleted  {seeker_profiles_count}
IT Users Deleted ........... {users_count}

====================================================
"""
        self.stdout.write(self.style.SUCCESS(summary))


if __name__ == "__main__":
    Command().handle()
