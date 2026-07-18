from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.it_user_role import ITUserRole
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileStatus, ProfileType
from apps.accounts.profiles.selectors.profile_selector import ProfileSelector
from apps.accounts.profiles.services.profile_completion_service import (
    ProfileCompletionService,
)
from apps.accounts.profiles.services.profile_validation_service import (
    ProfileValidationService,
)
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.academic_recruitment.models import (
    ProfessorDepartment,
    ProfessorProfile,
    Qualification,
)
from apps.academic_recruitment.repositories.profile_repository import (
    ProfessorProfileRepository,
)
from apps.colleges.models import College, CollegeDepartment, Department
from apps.colleges.repositories.college_repository import (
    CollegeMemberRepository,
    CollegeRepository,
)
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.colleges.services.college_service import CollegeService
from apps.core.exceptions.domain_exceptions import (
    ConflictException,
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.core.utils.strings import slugify
from apps.it_recruitment.models import (
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProfile,
    RecruiterProfile,
)
from apps.it_recruitment.repositories.experience_repository import (
    JobSeekerCertificationRepository,
    JobSeekerEducationRepository,
    JobSeekerExperienceRepository,
    JobSeekerProjectRepository,
)
from apps.it_recruitment.repositories.profile_repository import (
    JobSeekerProfileRepository,
    RecruiterProfileRepository,
)
from apps.jobs.models import JobSeekerSkill, Skill
from apps.jobs.repositories.seeker_skill_repository import (
    JobSeekerSkillRepository,
    SkillRepository,
)


class ProfileService(BaseService):
    """Unified profile lifecycle orchestration for all supported roles."""

    SEEKER_WRITABLE = {
        "first_name",
        "last_name",
        "phone",
        "gender",
        "date_of_birth",
        "city",
        "state",
        "country",
        "headline",
        "summary",
        "experience_years",
        "current_location",
        "preferred_location",
        "current_company",
        "current_salary",
        "expected_salary",
        "notice_period_days",
        "employment_type_preference",
        "work_mode_preference",
        "preferred_roles",
        "linkedin_url",
        "github_url",
        "portfolio_url",
        "personal_website",
        "languages",
        "profile_photo_id",
        "resume_file_id",
        "profile_visibility",
    }
    RECRUITER_WRITABLE = {
        "first_name",
        "last_name",
        "phone",
        "official_email",
        "designation",
        "department",
        "company_association",
        "profile_image_id",
        "profile_visibility",
    }
    PROFESSOR_WRITABLE = {
        "first_name",
        "last_name",
        "phone",
        "highest_qualification",
        "specialization",
        "research_interests",
        "experience_years",
        "teaching_experience_years",
        "industry_experience_years",
        "publications_count",
        "current_designation",
        "current_institution",
        "expected_salary",
        "preferred_locations",
        "profile_photo_id",
        "cv_file_id",
        "profile_visibility",
    }
    COLLEGE_WRITABLE = {
        "name",
        "college_type",
        "description",
        "website_url",
        "address_line",
        "city",
        "state",
        "pin_code",
        "accreditation",
        "aicte_code",
        "ugc_code",
        "naac_grade",
        "contact_phone",
        "contact_email",
        "established_year",
        "logo_file_id",
        "profile_visibility",
    }

    def __init__(self):
        self.selector = ProfileSelector()
        self.validation_service = ProfileValidationService()
        self.completion_service = ProfileCompletionService()
        self.seeker_repo = JobSeekerProfileRepository()
        self.recruiter_repo = RecruiterProfileRepository()
        self.professor_repo = ProfessorProfileRepository()
        self.college_repo = CollegeRepository()
        self.experience_repo = JobSeekerExperienceRepository()
        self.education_repo = JobSeekerEducationRepository()
        self.project_repo = JobSeekerProjectRepository()
        self.certification_repo = JobSeekerCertificationRepository()
        self.skill_repo = JobSeekerSkillRepository()
        self.skill_catalog_repo = SkillRepository()

    @BaseService.atomic
    def create_profile(
        self, *, user, profile_type: ProfileType | None = None, data: dict
    ):
        profile_type = profile_type or self.selector.resolve_profile_type(user)
        if not profile_type or profile_type == ProfileType.ADMIN:
            raise ValidationException(
                "Profile creation is not supported for this user type."
            )
        cleaned = self.validation_service.validate_create(profile_type, data)
        creators = {
            ProfileType.JOB_SEEKER: lambda: self._create_job_seeker(user, cleaned),
            ProfileType.RECRUITER: lambda: self._create_recruiter(user, cleaned),
            ProfileType.PROFESSOR: lambda: self._create_professor(user, cleaned),
            ProfileType.COLLEGE: lambda: self._create_college(user, cleaned),
        }
        profile = creators[profile_type]()
        return self._finalize(profile, profile_type)

    @BaseService.atomic
    def update_profile(
        self, *, user, data: dict, profile_type: ProfileType | None = None
    ):
        profile_type = profile_type or self.selector.resolve_profile_type(user)
        profile = self.selector.for_user(user, profile_type)
        if not profile:
            raise ResourceNotFoundException("Profile not found.")
        cleaned = self.validation_service.validate_update(profile_type, data)
        updaters = {
            ProfileType.JOB_SEEKER: lambda: self._update_job_seeker(
                profile, user, cleaned
            ),
            ProfileType.RECRUITER: lambda: self._update_recruiter(
                profile, cleaned, user.pk
            ),
            ProfileType.PROFESSOR: lambda: self._update_professor(
                profile, cleaned, user.pk
            ),
            ProfileType.COLLEGE: lambda: self._update_college(
                profile, cleaned, user.pk
            ),
        }
        updated = updaters[profile_type]()
        return self._finalize(updated, profile_type)

    def get_profile(self, user, profile_type: ProfileType | None = None):
        return self.selector.for_user(user, profile_type)

    def get_completion(self, user, profile_type: ProfileType | None = None) -> dict:
        profile_type = profile_type or self.selector.resolve_profile_type(user)
        profile = self.selector.for_user(user, profile_type)
        if not profile:
            raise ResourceNotFoundException("Profile not found.")
        percentage = self.completion_service.calculate(profile, profile_type)
        return {"profile_type": profile_type, "completion_percentage": percentage}

    @BaseService.atomic
    def deactivate_profile(self, user, profile_type: ProfileType | None = None):
        profile_type = profile_type or self.selector.resolve_profile_type(user)
        profile = self._require_profile(user, profile_type)
        repo = self._repo_for_type(profile_type)
        return repo.update(
            profile, profile_status=ProfileStatus.DEACTIVATED, updated_by_id=user.pk
        )

    @BaseService.atomic
    def activate_profile(self, user, profile_type: ProfileType | None = None):
        profile_type = profile_type or self.selector.resolve_profile_type(user)
        profile = self._require_profile(user, profile_type)
        repo = self._repo_for_type(profile_type)
        return self._finalize(
            repo.update(
                profile, profile_status=ProfileStatus.ACTIVE, updated_by_id=user.pk
            ),
            profile_type,
        )

    def _require_profile(self, user, profile_type: ProfileType):
        profile = self.selector.for_user(user, profile_type)
        if not profile:
            raise ResourceNotFoundException("Profile not found.")
        return profile

    def _repo_for_type(self, profile_type: ProfileType):
        mapping = {
            ProfileType.JOB_SEEKER: self.seeker_repo,
            ProfileType.RECRUITER: self.recruiter_repo,
            ProfileType.PROFESSOR: self.professor_repo,
            ProfileType.COLLEGE: self.college_repo,
        }
        return mapping[profile_type]

    def _finalize(self, profile, profile_type: ProfileType):
        if profile_type == ProfileType.JOB_SEEKER:
            from apps.it_recruitment.services.jobseeker_profile_completion_service import (
                JobSeekerProfileCompletionService,
            )

            JobSeekerProfileCompletionService().recalculate(profile)
            return profile
        if profile_type == ProfileType.PROFESSOR:
            completeness = self.completion_service.calculate(profile, profile_type)
            repo = self._repo_for_type(profile_type)
            profile = repo.update(profile, profile_completeness=completeness)
        return profile

    def _create_job_seeker(self, user: ITUser, data: dict) -> JobSeekerProfile:
        if self.selector.for_user(user, ProfileType.JOB_SEEKER):
            raise ConflictException("Job seeker profile already exists.")
        ITUserRole.objects.get_or_create(
            user=user, role=ITUserRoleType.JOB_SEEKER, defaults={"is_primary": True}
        )
        payload = self._pick(data, self.SEEKER_WRITABLE | {"first_name", "last_name"})
        profile = self.seeker_repo.create(user=user, created_by_id=user.pk, **payload)
        self._sync_seeker_nested(profile, data, user.pk)
        return profile

    def _create_recruiter(self, user: ITUser, data: dict) -> RecruiterProfile:
        if self.selector.for_user(user, ProfileType.RECRUITER):
            raise ConflictException("Recruiter profile already exists.")
        ITUserRole.objects.get_or_create(
            user=user, role=ITUserRoleType.RECRUITER, defaults={"is_primary": True}
        )
        payload = self._pick(
            data, self.RECRUITER_WRITABLE | {"first_name", "last_name"}
        )
        return self.recruiter_repo.create(user=user, created_by_id=user.pk, **payload)

    def _create_professor(self, user: ProfessorUser, data: dict) -> ProfessorProfile:
        if self.selector.for_user(user, ProfileType.PROFESSOR):
            raise ConflictException("Professor profile already exists.")
        payload = self._pick(
            data, self.PROFESSOR_WRITABLE | {"first_name", "last_name"}
        )
        profile = self.professor_repo.create(
            user=user, created_by_id=user.pk, **payload
        )
        self._sync_professor_nested(profile, data, user.pk)
        return profile

    def _create_college(self, user: CollegeUser, data: dict) -> College:
        college = CollegeService().create_college(college_user=user, data=data)
        if "department_ids" in data:
            college = self._update_college(
                college, {"department_ids": data["department_ids"]}, user.pk
            )
        return college

    def _update_job_seeker(
        self, profile: JobSeekerProfile, user, data: dict
    ) -> JobSeekerProfile:
        payload = self._pick(data, self.SEEKER_WRITABLE)
        profile = (
            self.seeker_repo.update(profile, updated_by_id=user.pk, **payload)
            if payload
            else profile
        )
        self._sync_seeker_nested(profile, data, user.pk)
        return profile

    def _update_recruiter(
        self, profile: RecruiterProfile, data: dict, actor_id
    ) -> RecruiterProfile:
        payload = self._pick(data, self.RECRUITER_WRITABLE)
        if not payload:
            return profile
        return self.recruiter_repo.update(profile, updated_by_id=actor_id, **payload)

    def _update_professor(
        self, profile: ProfessorProfile, data: dict, actor_id
    ) -> ProfessorProfile:
        payload = self._pick(data, self.PROFESSOR_WRITABLE)
        profile = (
            self.professor_repo.update(profile, updated_by_id=actor_id, **payload)
            if payload
            else profile
        )
        self._sync_professor_nested(profile, data, actor_id)
        return profile

    def _update_college(self, profile: College, data: dict, actor_id) -> College:
        payload = self._pick(data, self.COLLEGE_WRITABLE)
        profile = (
            self.college_repo.update(profile, updated_by_id=actor_id, **payload)
            if payload
            else profile
        )
        if "department_ids" in data:
            CollegeDepartment.objects.filter(college=profile, is_deleted=False).update(
                is_deleted=True
            )
            for department_id in data.get("department_ids") or []:
                department = Department.objects.filter(
                    pk=department_id, is_deleted=False
                ).first()
                if department:
                    CollegeDepartment.objects.create(
                        college=profile, department=department, created_by_id=actor_id
                    )
        return profile

    def _sync_seeker_nested(self, profile: JobSeekerProfile, data: dict, actor_id):
        if "skills" in data:
            desired_skill_ids: set = set()
            for skill_name in data.get("skills") or []:
                name = str(skill_name).strip()
                if not name:
                    continue
                skill, _ = Skill.objects.get_or_create(
                    name=name, defaults={"created_by_id": actor_id}
                )
                desired_skill_ids.add(skill.pk)
                link = JobSeekerSkill.objects.filter(
                    job_seeker=profile, skill=skill
                ).first()
                if link:
                    if link.is_deleted:
                        link.restore()
                else:
                    self.skill_repo.create(
                        job_seeker=profile, skill=skill, created_by_id=actor_id
                    )
            self.skill_repo.filter_by(job_seeker=profile, is_deleted=False).exclude(
                skill_id__in=desired_skill_ids
            ).update(is_deleted=True)
        if "experiences" in data:
            profile.experiences.filter(is_deleted=False).update(is_deleted=True)
            for item in data.get("experiences") or []:
                self.experience_repo.create(
                    job_seeker=profile, created_by_id=actor_id, **item
                )
        if "education" in data:
            profile.education.filter(is_deleted=False).update(is_deleted=True)
            for item in data.get("education") or []:
                self.education_repo.create(
                    job_seeker=profile, created_by_id=actor_id, **item
                )
        if "projects" in data:
            profile.projects.filter(is_deleted=False).update(is_deleted=True)
            for item in data.get("projects") or []:
                self.project_repo.create(
                    job_seeker=profile, created_by_id=actor_id, **item
                )
        if "certifications" in data:
            profile.certifications.filter(is_deleted=False).update(is_deleted=True)
            for item in data.get("certifications") or []:
                self.certification_repo.create(
                    job_seeker=profile, created_by_id=actor_id, **item
                )

    def _sync_professor_nested(self, profile: ProfessorProfile, data: dict, actor_id):
        if "department_ids" in data:
            ProfessorDepartment.objects.filter(
                professor=profile, is_deleted=False
            ).update(is_deleted=True)
            for department_id in data.get("department_ids") or []:
                department = Department.objects.filter(
                    pk=department_id, is_deleted=False
                ).first()
                if department:
                    ProfessorDepartment.objects.create(
                        professor=profile, department=department, created_by_id=actor_id
                    )
        if "qualifications" in data:
            profile.qualifications.filter(is_deleted=False).update(is_deleted=True)
            for item in data.get("qualifications") or []:
                qual_name = item.get("name") or item.get("qualification_name")
                if not qual_name:
                    continue
                qualification, _ = Qualification.objects.get_or_create(
                    name=qual_name.strip(), defaults={"created_by_id": actor_id}
                )
                from apps.academic_recruitment.models import ProfessorQualification

                ProfessorQualification.objects.create(
                    professor=profile,
                    qualification=qualification,
                    institution_name=item.get("institution_name", ""),
                    year_obtained=item.get("year_obtained"),
                    created_by_id=actor_id,
                )

    @staticmethod
    def _pick(data: dict, allowed: set[str]) -> dict:
        return {key: data[key] for key in allowed if key in data}

    # Backward-compatible helpers used by domain views
    def create_job_seeker_profile(
        self, *, user: ITUser, data: dict
    ) -> JobSeekerProfile:
        return self.create_profile(
            user=user, profile_type=ProfileType.JOB_SEEKER, data=data
        )

    def create_recruiter_profile(self, *, user: ITUser, data: dict) -> RecruiterProfile:
        return self.create_profile(
            user=user, profile_type=ProfileType.RECRUITER, data=data
        )
