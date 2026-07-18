from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.admin_panel.views.web import SuperAdminPortalMixin
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.core.constants.enums import DomainType
from apps.applications.models import JobApplication, FacultyApplication
from apps.applications.models.application import PlacementDetails
from apps.invoices.models.invoice import Invoice

class SuperAdminClaimCandidateSummaryAPIView(SuperAdminPortalMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            claim_id = kwargs.get("claim_id")
            
            # 1. Validate Claim Exists
            claim = get_object_or_404(GuaranteeClaim, pk=claim_id)
            
            # 2. Resolve Candidate & Application based on domain
            app = None
            candidate_data = {}
            app_data = {}
            placement_data = {}
            
            if claim.domain == DomainType.IT:
                app = JobApplication.objects.filter(pk=claim.application_entity_id, is_deleted=False).select_related("job_seeker__user", "job_posting", "company").first()
                if app:
                    candidate_data = {
                        "id": str(app.job_seeker.pk),
                        "name": app.applicant_name_snapshot,
                        "email": app.job_seeker.user.email if hasattr(app.job_seeker, "user") else "",
                        "phone": getattr(app.job_seeker, "phone_number", getattr(app.job_seeker.user, "phone_number", "")),
                        "domain": "IT",
                        "profile_photo": app.job_seeker.profile_photo.url if getattr(app.job_seeker, "profile_photo", None) else ""
                    }
                    app_data = {
                        "reference": str(app.pk),
                        "job_title": app.vacancy_title_snapshot,
                        "department": "IT",
                        "status": app.status,
                        "applied_at": app.applied_at.strftime("%Y-%m-%d %H:%M") if app.applied_at else ""
                    }
            elif claim.domain == DomainType.FACULTY:
                app = FacultyApplication.objects.filter(pk=claim.application_entity_id, is_deleted=False).select_related("professor__user", "vacancy", "college").first()
                if app:
                    candidate_data = {
                        "id": str(app.professor.pk),
                        "name": app.applicant_name_snapshot,
                        "email": app.professor.user.email if hasattr(app.professor, "user") else "",
                        "phone": getattr(app.professor, "phone", getattr(app.professor.user, "phone_number", "")),
                        "domain": "FACULTY",
                        "profile_photo": app.professor.profile_photo.url if getattr(app.professor, "profile_photo", None) else ""
                    }
                    app_data = {
                        "reference": str(app.pk),
                        "job_title": app.vacancy_title_snapshot,
                        "department": app.department,
                        "status": app.status,
                        "applied_at": app.applied_at.strftime("%Y-%m-%d %H:%M") if app.applied_at else ""
                    }
                    
            if not app:
                return JsonResponse({
                    "success": False,
                    "error": "Candidate relationship is no longer available. Application may have been deleted."
                }, status=404)
                
            # 3. Resolve Placement
            placement = PlacementDetails.objects.filter(application_id=app.pk, domain=claim.domain, is_deleted=False).first()
            if placement:
                placement_data = {
                    "recruiter_name": app.company_name_snapshot if claim.domain == DomainType.IT else app.college_name_snapshot,
                    "joining_status": "JOINED" if placement.actual_joining_date else "PENDING",
                    "joining_date": placement.actual_joining_date.strftime("%Y-%m-%d") if placement.actual_joining_date else "",
                    "annual_ctc": str(placement.agreed_salary) if placement.agreed_salary else ""
                }
            else:
                # Fallback for claims created without placement details
                placement_data = {
                    "recruiter_name": app.company_name_snapshot if claim.domain == DomainType.IT else app.college_name_snapshot,
                    "joining_status": "JOINED" if claim.joining_date else "UNKNOWN",
                    "joining_date": claim.joining_date.strftime("%Y-%m-%d") if claim.joining_date else "",
                    "annual_ctc": "N/A"
                }

            # 4. Guarantee Info
            guarantee_data = {
                "start_date": claim.guarantee_start_date.strftime("%Y-%m-%d") if claim.guarantee_start_date else "",
                "end_date": claim.guarantee_end_date.strftime("%Y-%m-%d") if claim.guarantee_end_date else "",
                "exit_date": claim.exit_date.strftime("%Y-%m-%d") if claim.exit_date else "",
                "days_employed": (claim.exit_date - claim.guarantee_start_date).days if claim.exit_date and claim.guarantee_start_date else 0,
                "eligible": True if (claim.exit_date and claim.guarantee_end_date and claim.exit_date <= claim.guarantee_end_date) else False
            }
            
            # 5. Claim Info
            claim_info = {
                "claim_number": claim.claim_number,
                "exit_reason": dict(claim._meta.get_field("exit_reason").choices).get(claim.exit_reason, claim.exit_reason),
                "requested_resolution": claim.get_claim_type_display(),
                "status": claim.get_status_display()
            }
            
            return JsonResponse({
                "success": True,
                "candidate": candidate_data,
                "application": app_data,
                "placement": placement_data,
                "guarantee": guarantee_data,
                "claim": claim_info
            })
            
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching candidate summary for claim: {str(exc)}", exc_info=True)
            return JsonResponse({
                "success": False,
                "error": "An unexpected error occurred while loading candidate details."
            }, status=500)
