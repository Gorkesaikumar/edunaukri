"""Job seeker Certificate Management Center — dashboard and list context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.constants.certificate_enums import (
    EXPIRING_SOON_DAYS,
    CertificateCategory,
)
from apps.it_recruitment.models import JobSeekerCertification, JobSeekerProfile
from apps.it_recruitment.services.certificate_management_service import (
    CertificateManagementService,
)
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)


@dataclass
class CertificateSummaryCard:
    key: str
    label: str
    value: str
    icon: str
    tone: str


@dataclass
class CertificateCard:
    id: str
    name: str
    organization: str
    category: str
    category_label: str
    issue_label: str
    expiry_label: str
    credential_id: str
    credential_url: str
    issue_date: str
    expiry_date: str
    status_key: str
    status_label: str
    status_badge: str
    file_name: str
    file_type: str
    has_file: bool
    is_pdf: bool
    is_image: bool
    preview_url: str | None
    download_url: str | None
    detail_api_url: str
    created_label: str


@dataclass
class CertificatePortalContext:
    summary: list[CertificateSummaryCard]
    certificates: list[CertificateCard]
    categories: list[tuple[str, str]]
    profile_contribution: int
    completion_percentage: int
    total_count: int
    page: int
    total_pages: int
    filters: dict
    upload_api_url: str
    list_api_url: str


class JobSeekerCertificatePortalService(BaseService):
    def __init__(self):
        self.mgmt = CertificateManagementService()

    def build(
        self,
        profile: JobSeekerProfile,
        *,
        page: int = 1,
        page_size: int = 9,
        q: str = "",
        category: str = "",
        status_filter: str = "",
        organization: str = "",
    ) -> CertificatePortalContext:
        qs = (
            profile.certifications.filter(is_deleted=False)
            .select_related("certificate_file")
            .order_by("-created_at")
        )
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(issuing_organization__icontains=q)
                | Q(credential_id__icontains=q)
            )
        if category:
            qs = qs.filter(category=category)
        if organization:
            qs = qs.filter(issuing_organization__icontains=organization)

        all_certs = list(qs)
        if status_filter:
            all_certs = [
                c for c in all_certs if self.mgmt.resolve_status(c).key == status_filter
            ]

        paginator = Paginator(all_certs, page_size)
        page_obj = paginator.get_page(page)
        completion = JobSeekerProfileCompletionService().get_dashboard_state(profile)
        user = profile.user
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)

        return CertificatePortalContext(
            summary=self._summary(profile, all_certs),
            certificates=[self._map_card(c, pu) for c in page_obj.object_list],
            categories=list(CertificateCategory.choices),
            profile_contribution=CertificateManagementService.PROFILE_CONTRIBUTION
            if all_certs
            else 0,
            completion_percentage=completion.percentage,
            total_count=len(all_certs),
            page=page_obj.number,
            total_pages=paginator.num_pages,
            filters={
                "q": q,
                "category": category,
                "status": status_filter,
                "organization": organization,
            },
            upload_api_url=pu("jobseeker_certificates_api"),
            list_api_url=pu("jobseeker_certificates_api"),
        )

    def _summary(
        self, profile, certs: list[JobSeekerCertification]
    ) -> list[CertificateSummaryCard]:
        today = timezone.localdate()
        recent_cutoff = timezone.now() - timedelta(days=30)
        expiring = sum(
            1
            for c in certs
            if c.expiry_date
            and today <= c.expiry_date <= today + timedelta(days=EXPIRING_SOON_DAYS)
        )
        verified = sum(1 for c in certs if c.is_verified)
        recent = sum(1 for c in certs if c.created_at >= recent_cutoff)
        return [
            CertificateSummaryCard(
                "total", "Total Certificates", str(len(certs)), "bi-award", "primary"
            ),
            CertificateSummaryCard(
                "verified",
                "Verified Certificates",
                str(verified),
                "bi-patch-check-fill",
                "success",
            ),
            CertificateSummaryCard(
                "expiring",
                "Expiring Soon",
                str(expiring),
                "bi-hourglass-split",
                "review",
            ),
            CertificateSummaryCard(
                "recent", "Recently Added", str(recent), "bi-plus-circle", "info"
            ),
            CertificateSummaryCard(
                "completion",
                "Profile Contribution",
                f"+{CertificateManagementService.PROFILE_CONTRIBUTION if certs else 0}%",
                "bi-pie-chart",
                "offer",
            ),
        ]

    def _map_card(self, cert: JobSeekerCertification, pu) -> CertificateCard:
        status = self.mgmt.resolve_status(cert)
        ext = ""
        file_name = ""
        if cert.certificate_file:
            file_name = cert.certificate_file.original_filename or ""
            if "." in file_name:
                ext = file_name.rsplit(".", 1)[-1].lower()
        issue = cert.issue_date.strftime("%b %Y") if cert.issue_date else "—"
        expiry = (
            cert.expiry_date.strftime("%b %d, %Y") if cert.expiry_date else "Lifetime"
        )
        cat_label = dict(CertificateCategory.choices).get(
            cert.category, cert.category.title()
        )
        has_file = bool(cert.certificate_file_id)
        return CertificateCard(
            id=str(cert.id),
            name=cert.name,
            organization=cert.issuing_organization or "—",
            category=cert.category,
            category_label=cat_label,
            issue_label=issue,
            expiry_label=expiry,
            credential_id=cert.credential_id or "",
            credential_url=cert.credential_url or "",
            issue_date=cert.issue_date.isoformat() if cert.issue_date else "",
            expiry_date=cert.expiry_date.isoformat() if cert.expiry_date else "",
            status_key=status.key,
            status_label=status.label,
            status_badge=status.badge,
            file_name=file_name,
            file_type=ext.upper() if ext else "—",
            has_file=has_file,
            is_pdf=ext == "pdf",
            is_image=ext in {"jpg", "jpeg", "png"},
            preview_url=pu("jobseeker_certificate_preview", certification_id=cert.pk)
            if has_file
            else None,
            download_url=pu("jobseeker_certificate_download", certification_id=cert.pk)
            if has_file
            else None,
            detail_api_url=pu(
                "jobseeker_certificate_detail_api", certification_id=cert.pk
            ),
            created_label=timezone.localtime(cert.created_at).strftime("%b %d, %Y"),
        )
