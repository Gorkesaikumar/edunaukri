import csv
from io import StringIO
from django.db.models import F

from django.contrib.auth import get_user_model

User = get_user_model()
from apps.applications.models import JobApplication, FacultyApplication
from apps.guarantee_claims.models import GuaranteeClaim
from apps.core.services.base import BaseService

VALID_REPORT_TYPES = frozenset(
    {
        "total_users",
        "it_placements",
        "faculty_placements",
        "refund_claims",
    }
)


class AdminReportService(BaseService):
    def get_report(self, report_type: str) -> dict:
        # Not used anymore since we generate CSV directly
        return {}

    def export_report(self, report_type: str, *, export_as: str = "csv"):
        if report_type not in VALID_REPORT_TYPES:
            raise ValueError(f"Invalid report type: {report_type}")
            
        output = StringIO()
        writer = csv.writer(output)
        
        if report_type == "total_users":
            writer.writerow(["User ID", "Full Name", "Email", "Phone Number", "User Type", "Domain", "Registration Date", "Account Status", "Last Login"])
            users = User.objects.all().order_by("-created_at")
            for u in users:
                writer.writerow([
                    u.pk, 
                    getattr(u, 'full_name', getattr(u, 'username', u.email)), 
                    u.email, 
                    getattr(u, 'phone', ''), 
                    getattr(u, 'role', 'user').title(), 
                    getattr(u, 'domain', 'N/A').upper(), 
                    u.created_at.strftime("%Y-%m-%d %H:%M") if getattr(u, 'created_at', None) else "", 
                    "Active" if u.is_active else "Inactive", 
                    u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else ""
                ])
            filename = "Total_Users_Report.csv"
            
        elif report_type == "it_placements":
            writer.writerow(["Candidate Name", "Recruiter Name", "Company Name", "Job Title", "Salary Package", "Joining Date", "Invoice Status", "Payment Status"])
            placements = JobApplication.objects.filter(status="hired").select_related("job_posting__company", "job_seeker")
            for p in placements:
                candidate = getattr(p.job_seeker, 'full_name', '') if p.job_seeker else ''
                company = p.job_posting.company
                member = company.members.first() if company else None
                recruiter = getattr(member.recruiter, 'full_name', '') if member and member.recruiter else ''
                company_name = company.name if company else ''
                title = p.job_posting.title if p.job_posting else ''
                
                # Fetch related invoice
                invoice = None
                if hasattr(p, 'fee') and hasattr(p.fee, 'invoice'):
                    invoice = p.fee.invoice
                    
                invoice_status = invoice.status.title() if invoice else "Pending"
                payment_status = "Paid" if invoice and invoice.status == 'paid' else "Unpaid"
                joining_date = p.hired_at.strftime("%Y-%m-%d") if getattr(p, 'hired_at', None) else ""
                salary = str(getattr(p, 'offered_salary', '0'))
                
                writer.writerow([candidate, recruiter, company_name, title, salary, joining_date, invoice_status, payment_status])
            filename = "IT_Placements_Report.csv"
            
        elif report_type == "faculty_placements":
            writer.writerow(["Candidate Name", "Institution Name", "Designation", "Department", "Salary Package", "Joining Date", "Invoice Status", "Payment Status"])
            placements = FacultyApplication.objects.filter(status="joined").select_related("vacancy__college", "professor")
            for p in placements:
                candidate = getattr(p.professor, 'full_name', '') if p.professor else ''
                college = p.vacancy.college if p.vacancy else None
                inst_name = college.name if college else ''
                designation = p.vacancy.title if p.vacancy else ''
                department = p.vacancy.department if p.vacancy else ''
                
                # Fetch related invoice
                invoice = None
                if hasattr(p, 'fee') and hasattr(p.fee, 'invoice'):
                    invoice = p.fee.invoice
                    
                invoice_status = invoice.status.title() if invoice else "Pending"
                payment_status = "Paid" if invoice and invoice.status == 'paid' else "Unpaid"
                joining_date = p.joined_at.strftime("%Y-%m-%d") if getattr(p, 'joined_at', None) else ""
                salary = str(getattr(p, 'offered_salary', '0'))
                
                writer.writerow([candidate, inst_name, designation, department, salary, joining_date, invoice_status, payment_status])
            filename = "Faculty_Placements_Report.csv"
            
        elif report_type == "refund_claims":
            writer.writerow(["Claim ID", "Candidate Name", "Recruiter / Institution", "Domain", "Invoice Number", "Claim Date", "Resolution Type", "Refund Amount", "Claim Status", "Approved By", "Refund Date"])
            claims = GuaranteeClaim.objects.all()
            for c in claims:
                candidate = c.candidate_name
                recruiter = c.recruiter_name
                domain = "IT" if c.domain == "it" else "Faculty"
                inv_num = str(c.invoice_id) if c.invoice_id else ""
                approved_by = str(c.approved_by_id) if c.approved_by_id else ""
                
                writer.writerow([
                    c.pk,
                    candidate,
                    recruiter,
                    domain,
                    inv_num,
                    c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
                    getattr(c, 'resolution', '').title(),
                    str(getattr(c, 'refund_amount', '0')),
                    c.status.title(),
                    approved_by,
                    c.resolved_at.strftime("%Y-%m-%d") if getattr(c, 'resolved_at', None) else ""
                ])
            filename = "Refund_Claims_Report.csv"
            
        return output.getvalue(), "text/csv", filename
