from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.workflow.faculty_engine import FacultyApplicationWorkflowEngine
from apps.applications.models import FacultyApplication, JobApplication
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.it_recruitment.selectors.profile_selector import (
    JobSeekerProfileSelector,
    RecruiterProfileSelector,
)


class ApplicationAuthorizationService(BaseService):
    """Role-aware authorization for application status changes."""

    def ensure_can_update_it_status(
        self, application: JobApplication, new_status: str, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        if new_status == JobApplicationStatus.WITHDRAWN:
            self._ensure_it_seeker_owner(application, actor)
            return
        if new_status in (
            JobApplicationStatus.OFFER_ACCEPTED,
            JobApplicationStatus.OFFER_DECLINED,
        ):
            if application.status == JobApplicationStatus.OFFER_RELEASED:
                self._ensure_it_seeker_owner(application, actor)
                return
        self._ensure_it_recruiter_for_job(application.job_posting, actor)

    def ensure_can_update_faculty_status(
        self, application: FacultyApplication, new_status: str, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        if (
            FacultyApplicationWorkflowEngine.normalize_status(new_status)
            == FacultyApplicationStatus.WITHDRAWN
        ):
            self._ensure_faculty_professor_owner(application, actor)
            return
        if new_status in (
            FacultyApplicationStatus.OFFER_ACCEPTED,
            FacultyApplicationStatus.OFFER_DECLINED,
        ):
            if application.status == FacultyApplicationStatus.OFFER_RELEASED:
                self._ensure_faculty_professor_owner(application, actor)
                return
        self._ensure_college_for_vacancy(application.vacancy, actor)

    def ensure_can_view_it_applications_for_job(self, job_posting, actor) -> None:
        if isinstance(actor, AdminUser):
            return
        self._ensure_it_recruiter_for_job(job_posting, actor)

    def ensure_can_view_faculty_applications_for_vacancy(self, vacancy, actor) -> None:
        if isinstance(actor, AdminUser):
            return
        self._ensure_college_for_vacancy(vacancy, actor)

    def ensure_can_view_it_application(
        self, application: JobApplication, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        seeker = JobSeekerProfileSelector().for_user(actor)
        if seeker and seeker.pk == application.job_seeker_id:
            return
        self._ensure_it_recruiter_for_job(application.job_posting, actor)

    def ensure_can_update_candidate_notes(
        self, application: JobApplication, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        self._ensure_it_seeker_owner(application, actor)

    def ensure_can_soft_delete_it_application(
        self, application: JobApplication, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        self._ensure_it_recruiter_for_job(application.job_posting, actor)

    def ensure_can_view_faculty_application(
        self, application: FacultyApplication, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        if isinstance(actor, ProfessorUser):
            from apps.academic_recruitment.selectors.profile_selector import (
                ProfessorProfileSelector,
            )

            professor = ProfessorProfileSelector().for_user(actor)
            if professor and professor.pk == application.professor_id:
                return
        self._ensure_college_for_vacancy(application.vacancy, actor)

    def ensure_can_update_professor_notes(
        self, application: FacultyApplication, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        self._ensure_faculty_professor_owner(application, actor)

    def ensure_can_soft_delete_faculty_application(
        self, application: FacultyApplication, actor
    ) -> None:
        if isinstance(actor, AdminUser):
            return
        self._ensure_college_for_vacancy(application.vacancy, actor)

    def _ensure_it_seeker_owner(self, application: JobApplication, actor) -> None:
        from apps.accounts.models import ITUser

        if not isinstance(actor, ITUser):
            raise PermissionDeniedException(
                "Only the applicant can perform this action."
            )
        seeker = JobSeekerProfileSelector().for_user(actor)
        if not seeker or seeker.pk != application.job_seeker_id:
            raise PermissionDeniedException(
                "Only the applicant can perform this action."
            )

    def _ensure_faculty_professor_owner(
        self, application: FacultyApplication, actor
    ) -> None:
        from apps.academic_recruitment.selectors.profile_selector import (
            ProfessorProfileSelector,
        )
        from apps.accounts.models import ProfessorUser

        if not isinstance(actor, ProfessorUser):
            raise PermissionDeniedException(
                "Only the applicant can perform this action."
            )
        professor = ProfessorProfileSelector().for_user(actor)
        if not professor or professor.pk != application.professor_id:
            raise PermissionDeniedException(
                "Only the applicant can perform this action."
            )

    def _ensure_it_recruiter_for_job(self, job_posting, actor) -> None:
        if not isinstance(actor, ITUser):
            raise PermissionDeniedException("Recruiter access required.")
        if ITUserRoleType.RECRUITER not in RoleAssignmentService().get_it_roles(actor):
            raise PermissionDeniedException("Recruiter access required.")
        recruiter = RecruiterProfileSelector().for_user(actor)
        if not recruiter:
            raise PermissionDeniedException("Recruiter profile required.")
        if (
            not CompanyMemberSelector()
            .for_recruiter(recruiter)
            .filter(company_id=job_posting.company_id)
            .exists()
        ):
            raise PermissionDeniedException(
                "You do not manage applications for this job."
            )

    def _ensure_college_for_vacancy(self, vacancy, actor) -> None:
        if not isinstance(actor, CollegeUser):
            raise PermissionDeniedException("College access required.")
        if (
            not CollegeMemberSelector()
            .for_user(actor)
            .filter(college_id=vacancy.college_id)
            .exists()
        ):
            raise PermissionDeniedException(
                "You do not manage applications for this vacancy."
            )
