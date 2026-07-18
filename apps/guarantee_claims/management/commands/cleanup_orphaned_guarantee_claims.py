from django.core.management.base import BaseCommand
from django.db import transaction
from apps.guarantee_claims.models.claim import GuaranteeClaim
from apps.applications.models import JobApplication, FacultyApplication
from apps.core.constants.enums import DomainType
from apps.guarantee_claims.constants.enums import ClaimStatus

class Command(BaseCommand):
    help = "Scans and cleans up Guarantee Claims that have orphaned or invalid application relationships."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting Guarantee Claims data integrity scan..."))
        
        claims = GuaranteeClaim.objects.all()
        
        total_claims = claims.count()
        deleted_count = 0
        archived_count = 0
        valid_count = 0
        
        for claim in claims:
            # Check domain
            if claim.domain == DomainType.IT:
                app_exists = JobApplication.objects.filter(pk=claim.application_entity_id, is_deleted=False).exists()
            elif claim.domain == DomainType.FACULTY:
                app_exists = FacultyApplication.objects.filter(pk=claim.application_entity_id, is_deleted=False).exists()
            else:
                app_exists = False
                
            if app_exists:
                valid_count += 1
                continue
                
            # Orphaned claim found
            self.stdout.write(self.style.WARNING(f"Orphaned claim detected: {claim.claim_number} (Domain: {claim.domain}, App ID: {claim.application_entity_id})"))
            
            with transaction.atomic():
                # Check for financial history / audit logs
                # If refunds exist, or resolution was made, we archive it
                has_financials = claim.refund_amount is not None or claim.status in [
                    ClaimStatus.REFUND_PROCESSING, ClaimStatus.REFUNDED, ClaimStatus.RESOLVED, ClaimStatus.REPLACEMENT_COMPLETED
                ]
                
                if has_financials:
                    claim.status = ClaimStatus.INVALID_DATA
                    claim.admin_notes = "Archived by cleanup script: Underlying application record is missing or deleted."
                    claim.save()
                    archived_count += 1
                    self.stdout.write(self.style.WARNING(f" -> Archived claim {claim.claim_number} (Financial history exists)"))
                else:
                    # Pure demo/mock data without real impact
                    claim.delete()
                    deleted_count += 1
                    self.stdout.write(self.style.ERROR(f" -> Deleted mock claim {claim.claim_number} (No financial history)"))
                    
        self.stdout.write(self.style.SUCCESS("-" * 50))
        self.stdout.write(self.style.SUCCESS("Guarantee Claims Cleanup Summary:"))
        self.stdout.write(self.style.SUCCESS(f"Total Scanned : {total_claims}"))
        self.stdout.write(self.style.SUCCESS(f"Valid Claims  : {valid_count}"))
        self.stdout.write(self.style.SUCCESS(f"Deleted       : {deleted_count}"))
        self.stdout.write(self.style.SUCCESS(f"Archived      : {archived_count}"))
        self.stdout.write(self.style.SUCCESS("-" * 50))
