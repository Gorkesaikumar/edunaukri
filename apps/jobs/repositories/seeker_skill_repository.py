from apps.core.repositories.crud import CRUDRepository
from apps.jobs.models import JobSeekerSkill, Skill


class SkillRepository(CRUDRepository):
    model = Skill


class JobSeekerSkillRepository(CRUDRepository):
    model = JobSeekerSkill
