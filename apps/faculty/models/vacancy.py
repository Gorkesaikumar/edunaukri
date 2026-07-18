from django.db import models
from django.core.validators import MinValueValidator

from apps.core.validators.common import validate_clean_text
from apps.accounts.models.college_user import CollegeUser
from apps.colleges.models import College, Department

from apps.core.models.base import AuditedBaseModel
from apps.faculty.constants.enums import (
    Designation,
    EmploymentType,
    QualificationLevel,
    RecruitmentCategory,
    SalaryVisibility,
    VacancyStatus,
    VacancyVisibility,
    WorkType,
)
from apps.faculty.managers import FacultyVacancyManager


class FacultyVacancy(AuditedBaseModel):
    # Backward-compatible aliases (legacy code references these nested enums).
    EmploymentType = EmploymentType
    VacancyStatus = VacancyStatus
    WorkType = WorkType

    # Relationships
    college = models.ForeignKey(
        College, on_delete=models.PROTECT, related_name="vacancies"
    )
    posted_by = models.ForeignKey(
        CollegeUser, on_delete=models.PROTECT, related_name="vacancies"
    )

    # Identity
    title = models.CharField(max_length=300, validators=[validate_clean_text])
    slug = models.SlugField(max_length=350)
    vacancy_code = models.CharField(max_length=50, blank=True, db_index=True)
    department = models.CharField(max_length=200, blank=True)
    designation = models.CharField(
        max_length=50, choices=Designation.choices, blank=True
    )

    # Descriptive content
    description = models.TextField(validators=[validate_clean_text])
    requirements = models.TextField(blank=True, validators=[validate_clean_text])
    roles_responsibilities = models.TextField(blank=True, validators=[validate_clean_text])
    teaching_responsibilities = models.TextField(blank=True, validators=[validate_clean_text])
    research_expectations = models.TextField(blank=True, validators=[validate_clean_text])
    administrative_responsibilities = models.TextField(blank=True, validators=[validate_clean_text])
    benefits = models.TextField(blank=True, validators=[validate_clean_text])
    facilities = models.TextField(blank=True, validators=[validate_clean_text])
    accommodation = models.CharField(max_length=255, blank=True, validators=[validate_clean_text])

    # Classification
    employment_type = models.CharField(
        max_length=50, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    work_type = models.CharField(
        max_length=20, choices=WorkType.choices, default=WorkType.ONSITE
    )
    recruitment_category = models.CharField(
        max_length=30, choices=RecruitmentCategory.choices, blank=True
    )
    contract_duration = models.CharField(max_length=120, blank=True)

    # Qualifications & specialization
    minimum_qualification = models.CharField(
        max_length=30, choices=QualificationLevel.choices, blank=True
    )
    preferred_qualification = models.CharField(
        max_length=30, choices=QualificationLevel.choices, blank=True
    )
    qualification_required = models.TextField(blank=True, validators=[validate_clean_text])
    specialization_required = models.TextField(blank=True, validators=[validate_clean_text])

    # Experience
    experience_min = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    experience_max = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    research_experience = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    industry_experience = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    # Compensation
    salary_min = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    salary_max = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    salary_currency = models.CharField(max_length=3, default="INR")
    salary_visibility = models.CharField(
        max_length=20,
        choices=SalaryVisibility.choices,
        default=SalaryVisibility.VISIBLE,
    )

    # Capacity & timeline
    vacancy_count = models.PositiveIntegerField(default=1)
    joining_date = models.DateField(null=True, blank=True)
    application_deadline = models.DateTimeField(null=True, blank=True)

    # Governance
    hiring_committee = models.CharField(max_length=300, blank=True)

    # Primary location
    country = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    campus = models.CharField(max_length=200, blank=True)

    # Flags & visibility
    visibility = models.CharField(
        max_length=20,
        choices=VacancyVisibility.choices,
        default=VacancyVisibility.PUBLIC,
    )
    is_featured = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    is_template = models.BooleanField(default=False)

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=VacancyStatus.choices,
        default=VacancyStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Snapshots & counters
    college_name_snapshot = models.CharField(max_length=300)
    application_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    objects = FacultyVacancyManager()

    class Meta:
        db_table = "faculty_vacancy"
        default_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(
                fields=["college", "slug"], name="unique_college_vacancy_slug"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "is_featured"]),
            models.Index(fields=["college", "status"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_published(self) -> bool:
        return self.status == VacancyStatus.PUBLISHED

    @property
    def is_draft(self) -> bool:
        return self.status == VacancyStatus.DRAFT

    @property
    def accepts_applications(self) -> bool:
        return self.status == VacancyStatus.PUBLISHED


class FacultyVacancyCampus(AuditedBaseModel):
    """Additional campuses supporting multi-campus faculty vacancies."""

    vacancy = models.ForeignKey(
        FacultyVacancy, on_delete=models.CASCADE, related_name="campuses"
    )
    country = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    campus = models.CharField(max_length=200, blank=True)
    work_type = models.CharField(
        max_length=20, choices=WorkType.choices, default=WorkType.ONSITE
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "faculty_vacancy_campus"

    def __str__(self):
        return f"{self.campus or self.city} ({self.vacancy_id})"


class FacultyVacancyDepartment(AuditedBaseModel):
    vacancy = models.ForeignKey(
        FacultyVacancy, on_delete=models.CASCADE, related_name="departments"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="vacancies"
    )

    class Meta:
        db_table = "faculty_vacancy_department"
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "department"], name="unique_vacancy_department"
            ),
        ]


class SavedVacancy(AuditedBaseModel):
    professor = models.ForeignKey(
        "academic_recruitment.ProfessorProfile",
        on_delete=models.CASCADE,
        related_name="saved_vacancies",
    )
    vacancy = models.ForeignKey(
        FacultyVacancy, on_delete=models.CASCADE, related_name="saved_by"
    )

    class Meta:
        db_table = "faculty_saved_vacancy"
        constraints = [
            models.UniqueConstraint(
                fields=["professor", "vacancy"], name="unique_saved_vacancy"
            ),
        ]
