"""Institution applications pipeline portal service."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models.college_user import CollegeUser
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.constants.transitions import ALLOWED_FACULTY_TRANSITIONS
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.academic_recruitment.services.college_portal_helpers import (
    institution_status_ui,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    initials_from_name,
    media_url,
)


@dataclass
class CollegeApplicationsPortalContext:
    applications: list[dict]
    pipeline: list[dict]
    stats: dict
    analytics: list[dict]
    status_options: list[dict]
    vacancy_filters: list[dict]
    filters: dict
    api_urls: dict
    pagination: dict


class CollegeApplicationsPortalService(BaseService):
    PER_PAGE = 20
    PIPELINE_CARD_LIMIT = 12

    ANALYTICS_KEYS = (
        ("applied", "New", "bi-inbox", "info", (FacultyApplicationStatus.APPLIED,)),
        (
            "review",
            "Under Review",
            "bi-search",
            "secondary",
            (FacultyApplicationStatus.UNDER_REVIEW,),
        ),
        (
            "shortlisted",
            "Shortlisted",
            "bi-check2-circle",
            "success",
            (
                FacultyApplicationStatus.SHORTLISTED,
                FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                FacultyApplicationStatus.DEPARTMENT_REVIEW,
                FacultyApplicationStatus.PRINCIPAL_REVIEW,
                FacultyApplicationStatus.MANAGEMENT_APPROVAL,
            ),
        ),
        (
            "interview",
            "Interviews",
            "bi-calendar-event",
            "accent",
            (
                FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                FacultyApplicationStatus.INTERVIEW_COMPLETED,
            ),
        ),
        (
            "offer",
            "Offers",
            "bi-envelope-check",
            "primary",
            (
                FacultyApplicationStatus.OFFER_RELEASED,
                FacultyApplicationStatus.OFFER_ACCEPTED,
                FacultyApplicationStatus.OFFER_DECLINED,
            ),
        ),
    )
    QUICK_STATUS_ACTIONS = {
        FacultyApplicationStatus.APPLIED: (
            FacultyApplicationStatus.SHORTLISTED,
            "Shortlist",
            "Shortlist this candidate",
        ),
        FacultyApplicationStatus.UNDER_REVIEW: (
            FacultyApplicationStatus.SHORTLISTED,
            "Shortlist",
            "Shortlist this candidate",
        ),
        FacultyApplicationStatus.SHORTLISTED: (
            FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            "Schedule Interview",
            "Move to interview scheduled",
        ),
        FacultyApplicationStatus.ACADEMIC_VERIFICATION: (
            FacultyApplicationStatus.DEPARTMENT_REVIEW,
            "Department Review",
            "Move to department review",
        ),
        FacultyApplicationStatus.DEPARTMENT_REVIEW: (
            FacultyApplicationStatus.PRINCIPAL_REVIEW,
            "Principal Review",
            "Move to principal review",
        ),
        FacultyApplicationStatus.PRINCIPAL_REVIEW: (
            FacultyApplicationStatus.MANAGEMENT_APPROVAL,
            "Mgmt Approval",
            "Move to management approval",
        ),
        FacultyApplicationStatus.MANAGEMENT_APPROVAL: (
            FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            "Schedule Interview",
            "Move to interview scheduled",
        ),
        FacultyApplicationStatus.INTERVIEW_SCHEDULED: (
            FacultyApplicationStatus.INTERVIEW_COMPLETED,
            "Mark Interview Complete",
            "Move to interview completed",
        ),
        FacultyApplicationStatus.INTERVIEW_COMPLETED: (
            FacultyApplicationStatus.OFFER_RELEASED,
            "Release Offer",
            "Move to offer released",
        ),
        FacultyApplicationStatus.OFFER_RELEASED: (
            FacultyApplicationStatus.OFFER_ACCEPTED,
            "Mark Offer Accepted",
            "Move to offer accepted",
        ),
        FacultyApplicationStatus.OFFER_ACCEPTED: (
            FacultyApplicationStatus.JOINED,
            "Mark Joined",
            "Move to joined",
        ),
    }
    OFFER_URL_PATTERN = re.compile(r"Offer Letter URL:\s*(\S+)", re.IGNORECASE)
    PIPELINE_STAGES = (
        ("applied", "Applied", FacultyApplicationStatus.APPLIED, "info"),
        (
            "under_review",
            "Under Review",
            FacultyApplicationStatus.UNDER_REVIEW,
            "secondary",
        ),
        (
            "shortlisted",
            "Shortlisted",
            FacultyApplicationStatus.SHORTLISTED,
            "success",
        ),
        (
            "interview_scheduled",
            "Interview Scheduled",
            FacultyApplicationStatus.INTERVIEW_SCHEDULED,
            "accent",
        ),
        (
            "interview_completed",
            "Interview Completed",
            FacultyApplicationStatus.INTERVIEW_COMPLETED,
            "accent",
        ),
        (
            "offer_released",
            "Offer Released",
            FacultyApplicationStatus.OFFER_RELEASED,
            "success",
        ),
        (
            "offer_accepted",
            "Offer Accepted",
            FacultyApplicationStatus.OFFER_ACCEPTED,
            "success",
        ),
        ("selected", "Selected", FacultyApplicationStatus.SELECTED, "success"),
        ("joining_in_progress", "Joining in Progress", FacultyApplicationStatus.JOINING_IN_PROGRESS, "info"),
        ("joined", "Joined", FacultyApplicationStatus.JOINED, "success"),
        ("rejected", "Rejected", FacultyApplicationStatus.REJECTED, "danger"),
    )

    def build(
        self,
        user: CollegeUser,
        *,
        q: str = "",
        status: str = "",
        vacancy_id: str = "",
        page: int = 1,
        sort: str = "newest",
    ) -> CollegeApplicationsPortalContext:
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        stats = FacultyApplicationStatisticsService().college_dashboard(user)
        by_status = stats.get("applications_by_status") or {}

        qs = (
            FacultyApplicationSelector()
            .for_college_user(user)
            .select_related(
                "vacancy",
                "professor",
                "professor__user",
                "professor__profile_photo",
                "professor__cv_file",
                "college",
            )
        )
        pipeline_qs = qs
        analytics_map = {item[0]: item[4] for item in self.ANALYTICS_KEYS}
        if status:
            if status in analytics_map:
                qs = qs.filter(status__in=analytics_map[status])
            elif status in FacultyApplicationStatus.values:
                qs = qs.filter(status=status)
        if vacancy_id:
            qs = qs.filter(vacancy_id=vacancy_id)
        if q:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=q)
                | Q(vacancy_title_snapshot__icontains=q)
                | Q(department__icontains=q)
            )

        sort_map = {
            "oldest": "applied_at",
            "updated": "-status_changed_at",
            "newest": "-applied_at",
        }
        order_field = sort_map.get(sort, "-applied_at")
        paginator = Paginator(qs.order_by(order_field), self.PER_PAGE)
        page_obj = paginator.get_page(page)

        vacancy_filters = [
            {"id": str(v.pk), "title": v.title}
            for v in FacultyVacancySelector()
            .for_college_user(user)
            .only("pk", "title")[:50]
        ]

        placeholder = "00000000-0000-0000-0000-000000000000"
        return CollegeApplicationsPortalContext(
            applications=[self._serialize_app(app, pu) for app in page_obj.object_list],
            pipeline=self._pipeline(pipeline_qs, pu),
            stats=stats,
            analytics=self._analytics(by_status),
            status_options=[
                {"value": choice.value, "label": choice.label}
                for choice in FacultyApplicationStatus
            ],
            vacancy_filters=vacancy_filters,
            filters={"q": q, "status": status, "vacancy_id": vacancy_id, "sort": sort},
            pagination={
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            api_urls={
                "list": pu("college_applications_list_api"),
                "status_template": pu(
                    "college_application_status_api", application_id=placeholder
                ),
                "notes_template": pu(
                    "college_application_notes_api", application_id=placeholder
                ),
                "cv_template": pu(
                    "college_application_cv_api", application_id=placeholder
                ),
            },
        )

    @classmethod
    def _analytics(cls, by_status: dict) -> list[dict]:
        items = []
        for key, label, icon, tone, statuses in cls.ANALYTICS_KEYS:
            items.append(
                {
                    "key": key,
                    "label": label,
                    "value": sum(by_status.get(s, 0) for s in statuses),
                    "icon": icon,
                    "tone": tone,
                }
            )
        items.append(
            {
                "key": "active",
                "label": "Active",
                "value": sum(
                    by_status.get(s, 0)
                    for s in FacultyApplicationStatus
                    if s
                    not in (
                        FacultyApplicationStatus.JOINED,
                        FacultyApplicationStatus.REJECTED,
                        FacultyApplicationStatus.WITHDRAWN,
                        FacultyApplicationStatus.EXPIRED,
                        FacultyApplicationStatus.OFFER_DECLINED,
                    )
                ),
                "icon": "bi-activity",
                "tone": "success",
            }
        )
        return items

    @staticmethod
    def _serialize_app(application, pu) -> dict:
        status_label, status_class = institution_status_ui(application.status)
        name = application.applicant_name_snapshot or "Faculty Applicant"
        professor = application.professor
        profile_photo_url = media_url(getattr(professor, "profile_photo", None))
        preferred_locations = getattr(professor, "preferred_locations", None) or []
        location_label = (
            ", ".join(str(loc) for loc in preferred_locations[:2] if loc)
            or "Not specified"
        )
        qualification_snapshot = application.qualification_snapshot or []
        top_qualification = (
            qualification_snapshot[0].get("qualification")
            if qualification_snapshot
            else ""
        )
        specialization = (
            (application.specialization_snapshot or {}).get("specialization")
            or getattr(professor, "specialization", "")
            or "General Faculty"
        )
        experience_years = (application.experience_snapshot or {}).get(
            "experience_years"
        ) or getattr(professor, "experience_years", None)
        exp_label = (
            f"{experience_years} yrs"
            if experience_years is not None
            else "Not specified"
        )
        raw_skills = [
            specialization,
            (application.specialization_snapshot or {}).get("research_interests"),
            application.department,
        ]
        skills = [
            str(skill).strip() for skill in raw_skills if str(skill or "").strip()
        ][:3]
        cv_available = bool(
            application.cv_file_id or getattr(professor, "cv_file_id", None)
        )
        cv_file = application.cv_file or getattr(professor, "cv_file", None)
        cv_file_name = getattr(cv_file, "original_filename", "") if cv_file else ""
        cv_mime_type = getattr(cv_file, "mime_type", "") if cv_file else ""
        quick_action = CollegeApplicationsPortalService.QUICK_STATUS_ACTIONS.get(
            application.status
        )
        allowed_targets = sorted(
            ALLOWED_FACULTY_TRANSITIONS.get(application.status, set())
        )
        shortlist_stages = {
            FacultyApplicationStatus.SHORTLISTED,
            FacultyApplicationStatus.ACADEMIC_VERIFICATION,
            FacultyApplicationStatus.DEPARTMENT_REVIEW,
            FacultyApplicationStatus.PRINCIPAL_REVIEW,
            FacultyApplicationStatus.MANAGEMENT_APPROVAL,
        }
        
        can_reject = application.status in {
            FacultyApplicationStatus.APPLIED,
            FacultyApplicationStatus.UNDER_REVIEW,
            FacultyApplicationStatus.INTERVIEW_COMPLETED,
        }
        
        can_shortlist = application.status in {
            FacultyApplicationStatus.APPLIED,
            FacultyApplicationStatus.UNDER_REVIEW,
        }
        
        # SHORTLISTED candidates can be directly scheduled for interview
        can_schedule = application.status in {
            FacultyApplicationStatus.SHORTLISTED,
            FacultyApplicationStatus.MANAGEMENT_APPROVAL,
            FacultyApplicationStatus.INTERVIEW_SCHEDULED,
        }
        rating_value = int(application.college_rating or 0)
        offer_letter_url = CollegeApplicationsPortalService._extract_offer_letter_url(
            application.internal_remarks or ""
        )
        can_send_offer = (
            application.status == FacultyApplicationStatus.INTERVIEW_COMPLETED
        )
        can_offer_accept = application.status == FacultyApplicationStatus.OFFER_RELEASED
        can_offer_decline = (
            application.status == FacultyApplicationStatus.OFFER_RELEASED
        )
        return {
            "id": str(application.pk),
            "candidate": name,
            "candidate_initials": initials_from_name(name, "FA"),
            "candidate_photo_url": profile_photo_url or "",
            "email": getattr(getattr(professor, "user", None), "email", "") or "",
            "phone": getattr(professor, "phone", "") or "",
            "location_label": location_label,
            "vacancy_title": application.vacancy_title_snapshot or "Faculty Role",
            "department": application.department or "",
            "qualification_label": top_qualification
            or getattr(professor, "highest_qualification", "")
            or "Not specified",
            "experience_label": exp_label,
            "skills": skills,
            "status": application.status,
            "status_label": status_label,
            "status_class": status_class,
            "applied_label": timezone.localtime(application.applied_at).strftime(
                "%b %d, %Y"
            ),
            "updated_label": timezone.localtime(application.status_changed_at).strftime(
                "%b %d, %Y"
            )
            if application.status_changed_at
            else "—",
            "profile_url": pu(
                "college_application_profile_api", application_id=application.pk
            ),
            "status_url": pu(
                "college_application_status_api", application_id=application.pk
            ),
            "notes_url": pu(
                "college_application_notes_api", application_id=application.pk
            ),
            "detail_url": pu(
                "college_application_detail", application_id=application.pk
            ),
            "cv_preview_url": pu(
                "college_application_cv_api", application_id=application.pk
            )
            + "?preview=1",
            "cv_download_url": pu(
                "college_application_cv_api", application_id=application.pk
            ),
            "cv_file_name": cv_file_name,
            "cv_mime_type": cv_mime_type,
            "contact_url": f"mailto:{getattr(getattr(professor, 'user', None), 'email', '')}"
            if getattr(getattr(professor, "user", None), "email", "")
            else "",
            "cv_available": cv_available,
            "college_notes": application.college_notes or "",
            "internal_remarks": application.internal_remarks or "",
            "college_rating": rating_value,
            "offer_letter_url": offer_letter_url,
            "offer_stage": CollegeApplicationsPortalService._offer_stage_label(
                application.status
            ),
            "can_send_offer": can_send_offer,
            "can_offer_accept": can_offer_accept,
            "can_offer_decline": can_offer_decline,
            "permissions": {
                "can_view_profile": True,
                "can_preview_resume": cv_available,
                "can_download_resume": cv_available,
                "can_shortlist": can_shortlist,
                "can_reject": can_reject,
                "can_add_notes": True,
                "can_schedule_interview": can_schedule,
                "can_contact": True,
            },
            "quick_action": {
                "status": quick_action[0] if quick_action else "",
                "label": quick_action[1] if quick_action else "",
                "hint": quick_action[2] if quick_action else "",
            }
            if quick_action
            else None,
            "allowed_targets": allowed_targets,
            "reject_action": {
                "status": FacultyApplicationStatus.REJECTED,
                "label": "Reject",
                "hint": "Reject this candidate",
            }
            if can_reject
            else None,
        }

    @classmethod
    def _pipeline(cls, qs, pu) -> list[dict]:
        stage_statuses = [
            stage[2]
            for stage in cls.PIPELINE_STAGES
            if stage[2] != FacultyApplicationStatus.REJECTED
        ]
        terminal_rejected_statuses = {
            FacultyApplicationStatus.REJECTED,
            FacultyApplicationStatus.WITHDRAWN,
            FacultyApplicationStatus.EXPIRED,
            FacultyApplicationStatus.OFFER_DECLINED,
        }
        stage_qs = qs.filter(
            status__in=stage_statuses + [FacultyApplicationStatus.REJECTED]
        )
        apps = list(
            stage_qs.select_related(
                "professor", "professor__profile_photo", "professor__user"
            ).order_by("-status_changed_at", "-applied_at")[:500]
        )
        grouped: dict[str, list] = {}
        for app in apps:
            status = app.status
            if status in terminal_rejected_statuses:
                status = FacultyApplicationStatus.REJECTED
            grouped.setdefault(status, []).append(app)

        columns = []
        for key, label, target_status, tone in cls.PIPELINE_STAGES:
            cards = grouped.get(target_status, [])
            serialized_cards = []
            for app in cards[: cls.PIPELINE_CARD_LIMIT]:
                allowed_targets = sorted(
                    ALLOWED_FACULTY_TRANSITIONS.get(app.status, set())
                )
                serialized_cards.append(
                    {
                        "id": str(app.pk),
                        "candidate": app.applicant_name_snapshot or "Faculty Applicant",
                        "candidate_initials": initials_from_name(
                            app.applicant_name_snapshot or "", "FA"
                        ),
                        "candidate_photo_url": media_url(
                            getattr(app.professor, "profile_photo", None)
                        )
                        or "",
                        "vacancy_title": app.vacancy_title_snapshot or "Faculty Role",
                        "experience_label": cls._experience_label(app),
                        "applied_label": timezone.localtime(app.applied_at).strftime(
                            "%b %d"
                        ),
                        "detail_url": pu(
                            "college_application_detail", application_id=app.pk
                        ),
                        "status_url": pu(
                            "college_application_status_api", application_id=app.pk
                        ),
                        "allowed_targets": allowed_targets,
                        "can_drag": bool(allowed_targets),
                    }
                )
            columns.append(
                {
                    "key": key,
                    "label": label,
                    "target_status": target_status,
                    "tone": tone,
                    "count": len(cards),
                    "cards": serialized_cards,
                }
            )
        return columns

    @staticmethod
    def _experience_label(application) -> str:
        years = (application.experience_snapshot or {}).get(
            "experience_years"
        ) or getattr(application.professor, "experience_years", None)
        if years is None:
            return "N/A"
        return f"{years} yrs"

    @classmethod
    def _extract_offer_letter_url(cls, remarks: str) -> str:
        match = cls.OFFER_URL_PATTERN.search(remarks or "")
        return match.group(1).strip() if match else ""

    @staticmethod
    def _offer_stage_label(status: str) -> str:
        if status == FacultyApplicationStatus.OFFER_RELEASED:
            return "Offer Released"
        if status == FacultyApplicationStatus.OFFER_ACCEPTED:
            return "Offer Accepted"
        if status == FacultyApplicationStatus.OFFER_DECLINED:
            return "Offer Declined"
        return ""

    @staticmethod
    def filters_query(page: int, filters: dict) -> str:
        query = {k: v for k, v in filters.items() if v}
        if page > 1:
            query["page"] = page
        encoded = urlencode(query)
        return f"?{encoded}" if encoded else ""
