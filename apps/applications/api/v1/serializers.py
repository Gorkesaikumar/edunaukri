from rest_framework import serializers

from apps.applications.constants.enums import ApplicationSource, JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.constants.interview_enums import (
    InterviewMode,
    InterviewRoundType,
    InterviewStatus,
)
from apps.applications.models import (
    FacultyApplication,
    FacultyApplicationStatusHistory,
    FacultyApplicationTimelineEvent,
    JobApplication,
    JobApplicationInterview,
    JobApplicationStatusHistory,
    JobApplicationTimelineEvent,
)


class JobApplicationSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    hired_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "job_posting",
            "job_seeker",
            "company_id",
            "status",
            "cover_letter",
            "applied_at",
            "status_changed_at",
            "placed_at",
            "hired_at",
            "rejection_reason",
            "applicant_name_snapshot",
            "job_title_snapshot",
            "company_name_snapshot",
            "resume_file",
            "resume_snapshot",
            "expected_salary",
            "notice_period",
            "current_location",
            "source",
            "recruiter_notes",
            "candidate_notes",
            "internal_remarks",
        )
        read_only_fields = fields


class JobApplicationCreateSerializer(serializers.Serializer):
    job_posting_id = serializers.UUIDField()
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    resume_file_id = serializers.UUIDField(required=False, allow_null=True)
    expected_salary = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    notice_period = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )
    current_location = serializers.CharField(
        required=False, allow_blank=True, max_length=200
    )
    source = serializers.ChoiceField(choices=ApplicationSource.choices, required=False)


class JobApplicationInterviewScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    round_type = serializers.ChoiceField(
        choices=InterviewRoundType.choices, required=False
    )
    round_label = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    interview_type = serializers.CharField(required=False, max_length=120)
    mode = serializers.ChoiceField(choices=InterviewMode.choices, required=False)
    duration_minutes = serializers.IntegerField(
        required=False, min_value=15, max_value=480
    )
    timezone_label = serializers.CharField(required=False, max_length=64)
    meet_url = serializers.URLField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True, max_length=300)
    panel = serializers.ListField(child=serializers.DictField(), required=False)
    instructions = serializers.CharField(required=False, allow_blank=True)
    required_documents = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    transition_status = serializers.BooleanField(required=False, default=True)


class JobApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=JobApplicationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    interview = JobApplicationInterviewScheduleSerializer(required=False)


class JobApplicationNotesSerializer(serializers.Serializer):
    recruiter_notes = serializers.CharField(required=False, allow_blank=True)
    internal_remarks = serializers.CharField(required=False, allow_blank=True)
    candidate_notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one notes field.")
        return attrs


class JobApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplicationStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by_id",
            "changed_by_domain",
            "notes",
            "changed_at",
        )
        read_only_fields = fields


class JobApplicationTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplicationTimelineEvent
        fields = (
            "id",
            "event_type",
            "from_status",
            "to_status",
            "actor_id",
            "actor_domain",
            "notes",
            "metadata",
            "occurred_at",
        )
        read_only_fields = fields


class FacultyApplicationSerializer(serializers.ModelSerializer):
    college_id = serializers.UUIDField(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = FacultyApplication
        fields = (
            "id",
            "vacancy",
            "professor",
            "college_id",
            "status",
            "cover_letter",
            "applied_at",
            "status_changed_at",
            "placed_at",
            "joined_at",
            "rejection_reason",
            "applicant_name_snapshot",
            "vacancy_title_snapshot",
            "college_name_snapshot",
            "cv_file",
            "cv_snapshot",
            "qualification_snapshot",
            "specialization_snapshot",
            "experience_snapshot",
            "certificates_snapshot",
            "department",
            "expected_salary",
            "current_institution",
            "current_designation",
            "research_publications_count",
            "source",
            "college_notes",
            "professor_notes",
            "internal_remarks",
        )
        read_only_fields = fields


class FacultyApplicationCreateSerializer(serializers.Serializer):
    vacancy_id = serializers.UUIDField()
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    cv_file_id = serializers.UUIDField(required=False, allow_null=True)
    expected_salary = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    current_institution = serializers.CharField(
        required=False, allow_blank=True, max_length=300
    )
    current_designation = serializers.CharField(
        required=False, allow_blank=True, max_length=150
    )
    source = serializers.ChoiceField(choices=ApplicationSource.choices, required=False)


class FacultyApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FacultyApplicationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class FacultyApplicationNotesSerializer(serializers.Serializer):
    college_notes = serializers.CharField(required=False, allow_blank=True)
    internal_remarks = serializers.CharField(required=False, allow_blank=True)
    professor_notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one notes field.")
        return attrs


class FacultyApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyApplicationStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by_id",
            "changed_by_domain",
            "notes",
            "changed_at",
        )
        read_only_fields = fields


class FacultyApplicationTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyApplicationTimelineEvent
        fields = (
            "id",
            "event_type",
            "from_status",
            "to_status",
            "actor_id",
            "actor_domain",
            "notes",
            "metadata",
            "occurred_at",
        )
        read_only_fields = fields


class JobApplicationInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplicationInterview
        fields = (
            "id",
            "application",
            "interview_id",
            "round_type",
            "round_label",
            "interview_type",
            "mode",
            "scheduled_at",
            "duration_minutes",
            "timezone_label",
            "meet_url",
            "location",
            "panel",
            "instructions",
            "required_documents",
            "status",
            "candidate_confirmed",
            "candidate_confirmed_at",
            "feedback",
            "feedback_shared",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class JobApplicationInterviewUpdateSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField(required=False)
    round_type = serializers.ChoiceField(
        choices=InterviewRoundType.choices, required=False
    )
    round_label = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    interview_type = serializers.CharField(required=False, max_length=120)
    mode = serializers.ChoiceField(choices=InterviewMode.choices, required=False)
    duration_minutes = serializers.IntegerField(
        required=False, min_value=15, max_value=480
    )
    timezone_label = serializers.CharField(required=False, max_length=64)
    meet_url = serializers.URLField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True, max_length=300)
    panel = serializers.ListField(child=serializers.DictField(), required=False)
    instructions = serializers.CharField(required=False, allow_blank=True)
    required_documents = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class JobApplicationInterviewScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    round_type = serializers.ChoiceField(
        choices=InterviewRoundType.choices, required=False
    )
    round_label = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    interview_type = serializers.CharField(required=False, max_length=120)
    mode = serializers.ChoiceField(choices=InterviewMode.choices, required=False)
    duration_minutes = serializers.IntegerField(
        required=False, min_value=15, max_value=480
    )
    timezone_label = serializers.CharField(required=False, max_length=64)
    meet_url = serializers.URLField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True, max_length=300)
    panel = serializers.ListField(child=serializers.DictField(), required=False)
    instructions = serializers.CharField(required=False, allow_blank=True)
    required_documents = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    transition_status = serializers.BooleanField(required=False, default=True)


class JobApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=JobApplicationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    interview = JobApplicationInterviewScheduleSerializer(required=False)


class JobApplicationNotesSerializer(serializers.Serializer):
    recruiter_notes = serializers.CharField(required=False, allow_blank=True)
    internal_remarks = serializers.CharField(required=False, allow_blank=True)
    candidate_notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one notes field.")
        return attrs


class JobApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplicationStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by_id",
            "changed_by_domain",
            "notes",
            "changed_at",
        )
        read_only_fields = fields


class JobApplicationTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplicationTimelineEvent
        fields = (
            "id",
            "event_type",
            "from_status",
            "to_status",
            "actor_id",
            "actor_domain",
            "notes",
            "metadata",
            "occurred_at",
        )
        read_only_fields = fields


class FacultyApplicationSerializer(serializers.ModelSerializer):
    college_id = serializers.UUIDField(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = FacultyApplication
        fields = (
            "id",
            "vacancy",
            "professor",
            "college_id",
            "status",
            "cover_letter",
            "applied_at",
            "status_changed_at",
            "placed_at",
            "joined_at",
            "rejection_reason",
            "applicant_name_snapshot",
            "vacancy_title_snapshot",
            "college_name_snapshot",
            "cv_file",
            "cv_snapshot",
            "qualification_snapshot",
            "specialization_snapshot",
            "experience_snapshot",
            "certificates_snapshot",
            "department",
            "expected_salary",
            "current_institution",
            "current_designation",
            "research_publications_count",
            "source",
            "college_notes",
            "professor_notes",
            "internal_remarks",
        )
        read_only_fields = fields


class FacultyApplicationCreateSerializer(serializers.Serializer):
    vacancy_id = serializers.UUIDField()
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    cv_file_id = serializers.UUIDField(required=False, allow_null=True)
    expected_salary = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    current_institution = serializers.CharField(
        required=False, allow_blank=True, max_length=300
    )
    current_designation = serializers.CharField(
        required=False, allow_blank=True, max_length=150
    )
    source = serializers.ChoiceField(choices=ApplicationSource.choices, required=False)


class FacultyApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FacultyApplicationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class FacultyApplicationNotesSerializer(serializers.Serializer):
    college_notes = serializers.CharField(required=False, allow_blank=True)
    internal_remarks = serializers.CharField(required=False, allow_blank=True)
    professor_notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one notes field.")
        return attrs


class FacultyApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyApplicationStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by_id",
            "changed_by_domain",
            "notes",
            "changed_at",
        )
        read_only_fields = fields


class FacultyApplicationTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyApplicationTimelineEvent
        fields = (
            "id",
            "event_type",
            "from_status",
            "to_status",
            "actor_id",
            "actor_domain",
            "notes",
            "metadata",
            "occurred_at",
        )
        read_only_fields = fields


class JobApplicationInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplicationInterview
        fields = (
            "id",
            "application",
            "interview_id",
            "round_type",
            "round_label",
            "interview_type",
            "mode",
            "scheduled_at",
            "duration_minutes",
            "timezone_label",
            "meet_url",
            "location",
            "panel",
            "instructions",
            "required_documents",
            "status",
            "candidate_confirmed",
            "candidate_confirmed_at",
            "feedback",
            "feedback_shared",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class JobApplicationInterviewUpdateSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField(required=False)
    round_type = serializers.ChoiceField(
        choices=InterviewRoundType.choices, required=False
    )
    round_label = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    interview_type = serializers.CharField(required=False, max_length=120)
    mode = serializers.ChoiceField(choices=InterviewMode.choices, required=False)
    duration_minutes = serializers.IntegerField(
        required=False, min_value=15, max_value=480
    )
    timezone_label = serializers.CharField(required=False, max_length=64)
    meet_url = serializers.URLField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True, max_length=300)
    panel = serializers.ListField(child=serializers.DictField(), required=False)
    instructions = serializers.CharField(required=False, allow_blank=True)
    required_documents = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    feedback = serializers.DictField(required=False)
    feedback_shared = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=InterviewStatus.choices, required=False)


class AdminJobSeekerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = serializers.CharField(source="phone", read_only=True)
    experience = serializers.IntegerField(source="experience_years", read_only=True)
    location = serializers.CharField(source="current_location", read_only=True)
    company = serializers.CharField(source="current_company", read_only=True)
    designation = serializers.CharField(source="headline", read_only=True)

    class Meta:
        from apps.it_recruitment.models import JobSeekerProfile

        model = JobSeekerProfile
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "designation",
            "experience",
            "company",
            "location",
        )


class AdminJobApplicationSerializer(JobApplicationSerializer):
    applicant_details = AdminJobSeekerProfileSerializer(
        source="job_seeker", read_only=True
    )
    resume_url = serializers.SerializerMethodField()

    class Meta(JobApplicationSerializer.Meta):
        fields = JobApplicationSerializer.Meta.fields + (
            "applicant_details",
            "resume_url",
        )

    def get_resume_url(self, obj):
        if obj.resume_file_id:
            return f"/api/v1/documents/{obj.resume_file_id}/download/"
        return None


class AdminProfessorProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = serializers.CharField(source="phone", read_only=True)
    experience = serializers.IntegerField(source="experience_years", read_only=True)
    institution = serializers.CharField(source="current_institution", read_only=True)
    designation = serializers.CharField(source="current_designation", read_only=True)

    class Meta:
        from apps.academic_recruitment.models import ProfessorProfile

        model = ProfessorProfile
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "designation",
            "experience",
            "institution",
        )


class AdminFacultyApplicationSerializer(FacultyApplicationSerializer):
    applicant_details = AdminProfessorProfileSerializer(
        source="professor", read_only=True
    )
    resume_url = serializers.SerializerMethodField()

    class Meta(FacultyApplicationSerializer.Meta):
        fields = FacultyApplicationSerializer.Meta.fields + (
            "applicant_details",
            "resume_url",
        )

    def get_resume_url(self, obj):
        if obj.cv_file_id:
            return f"/api/v1/documents/{obj.cv_file_id}/download/"
        return None
