import json
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.admin_panel.views.web import SuperAdminPortalMixin
from apps.companies.models import Company, CompanyMember
from apps.colleges.models import College, CollegeMember
from apps.jobs.models import JobPosting
from apps.applications.models import JobApplication, FacultyApplication
from django.conf import settings

class SuperAdminOrganizationDetailAPIView(SuperAdminPortalMixin, View):
    def _get_logo_url(self, logo_file):
        if not logo_file or not getattr(logo_file, "storage_path", ""):
            return None
        path = str(logo_file.storage_path).replace("\\", "/")
        if path.startswith(("http://", "https://", "/")):
            return path
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return f"{media_url}{path.lstrip('/')}"

    def get(self, request, org_id, *args, **kwargs):
        org_type = request.GET.get("type", "company")
        
        try:
            if org_type == "college":
                org = get_object_or_404(College, pk=org_id, is_deleted=False)
                members_count = CollegeMember.objects.filter(college=org, is_deleted=False).count()
                jobs_count = 0  # Assuming colleges use Vacancy, but we can return 0 or fetch Vacancy count
                hires_count = FacultyApplication.objects.filter(college=org, status="placed").count()
                return JsonResponse({
                    "success": True,
                    "data": {
                        "name": org.name,
                        "logo_url": self._get_logo_url(org.logo_file),
                        "id": str(org.id),
                        "type": "Academic Institution",
                        "registration_number": org.aicte_code or org.ugc_code or "N/A",
                        "email": org.contact_email,
                        "phone": org.contact_phone,
                        "website": org.website_url,
                        "address": org.address_line or "N/A",
                        "city": org.city or "N/A",
                        "state": org.state or "N/A",
                        "country": org.country or "N/A",
                        "registered_date": org.created_at.strftime("%B %d, %Y"),
                        "subscription_plan": "Standard",
                        "subscription_status": "Active" if org.is_active else "Inactive",
                        "subscription_expiry": "Lifetime",
                        "total_recruiters": members_count,
                        "active_recruiters": CollegeMember.objects.filter(college=org, is_active=True, is_deleted=False).count(),
                        "last_login": "2 Days Ago", # Mock
                        "total_jobs": jobs_count,
                        "total_hires": hires_count,
                        "status": "Active" if org.is_active else "Deactivated",
                    }
                })
            else:
                org = get_object_or_404(Company, pk=org_id, is_deleted=False)
                members_count = CompanyMember.objects.filter(company=org, is_deleted=False).count()
                jobs_count = JobPosting.objects.filter(company=org, is_deleted=False).count()
                hires_count = JobApplication.objects.filter(company=org, status="placed").count()
                return JsonResponse({
                    "success": True,
                    "data": {
                        "name": org.name,
                        "logo_url": self._get_logo_url(org.logo_file),
                        "id": str(org.id),
                        "type": "IT Employer",
                        "registration_number": org.gst_number or "N/A",
                        "email": org.email,
                        "phone": org.phone,
                        "website": org.website_url,
                        "address": org.address_line or "N/A",
                        "city": org.city or "N/A",
                        "state": org.state or "N/A",
                        "country": org.country or "N/A",
                        "registered_date": org.created_at.strftime("%B %d, %Y"),
                        "subscription_plan": "Standard",
                        "subscription_status": "Active" if org.is_active else "Inactive",
                        "subscription_expiry": "Lifetime",
                        "total_recruiters": members_count,
                        "active_recruiters": CompanyMember.objects.filter(company=org, is_active=True, is_deleted=False).count(),
                        "last_login": "1 Day Ago", # Mock
                        "total_jobs": jobs_count,
                        "total_hires": hires_count,
                        "status": "Active" if org.is_active else "Deactivated",
                    }
                })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
