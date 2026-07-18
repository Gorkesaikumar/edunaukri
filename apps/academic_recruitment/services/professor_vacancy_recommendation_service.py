"""Published faculty vacancy recommendations for professor dashboards."""

from __future__ import annotations

from apps.academic_recruitment.models import ProfessorProfile
from apps.faculty.models import SavedVacancy
from apps.faculty.selectors.vacancy_selector import PublicFacultyVacancySelector
from apps.core.services.base import BaseService


class ProfessorVacancyRecommendationService(BaseService):
    DEFAULT_LIMIT = 4

    def recommend(self, profile: ProfessorProfile, *, limit: int | None = None):
        limit = limit or self.DEFAULT_LIMIT
        applied_ids = set(
            profile.applications.filter(is_deleted=False).values_list(
                "vacancy_id", flat=True
            )
        )
        queryset = (
            PublicFacultyVacancySelector()
            .published()
            .select_related("college", "college__logo_file")
            .exclude(pk__in=applied_ids)
        )

        specialization = (profile.specialization or "").strip().lower()
        research = (profile.research_interests or "").strip().lower()
        qualification = (profile.highest_qualification or "").strip().lower()
        exp_years = profile.teaching_experience_years or profile.experience_years or 0
        department_names = list(
            profile.departments.filter(is_deleted=False).values_list(
                "department__name", flat=True
            )
        )
        preferred = [
            str(loc).lower() for loc in (profile.preferred_locations or []) if loc
        ]
        
        parsed_resume = getattr(profile, "parsed_resume", None)
        parsed_skills = []
        if parsed_resume and parsed_resume.status == "success":
            parsed_skills = [s.lower() for s in parsed_resume.extracted_skills]


        scored: list[tuple[int, object]] = []
        for vacancy in queryset[:100]:
            score, explanation = self._score_vacancy(
                vacancy,
                specialization=specialization,
                research=research,
                qualification=qualification,
                exp_years=exp_years,
                department_names=department_names,
                preferred_locations=preferred,
                parsed_skills=parsed_skills,
                profile=profile,
            )
            vacancy.match_percentage = score
            vacancy.match_explanation = explanation
            scored.append((score, vacancy))

        scored.sort(
            key=lambda item: (
                -item[0],
                -(item[1].published_at.timestamp() if item[1].published_at else 0),
            )
        )
        return [vacancy for _, vacancy in scored[:limit]]

    def saved_vacancy_ids(self, profile: ProfessorProfile) -> set:
        return set(
            SavedVacancy.objects.filter(
                professor=profile, is_deleted=False
            ).values_list("vacancy_id", flat=True)
        )

    @staticmethod
    def _score_vacancy(
        vacancy,
        *,
        specialization: str,
        research: str,
        qualification: str,
        exp_years: int,
        department_names: list[str],
        preferred_locations: list[str],
        parsed_skills: list[str],
        profile: ProfessorProfile,
    ) -> tuple[int, str]:
        score = 48  # Base relevance percentage
        reasons = []

        if vacancy.is_featured:
            score += 4
        if vacancy.is_urgent:
            score += 3

        haystack = " ".join(
            filter(
                None,
                [
                    vacancy.title,
                    vacancy.department,
                    vacancy.specialization_required,
                    vacancy.qualification_required,
                    vacancy.roles_responsibilities,
                    vacancy.teaching_responsibilities,
                    vacancy.college_name_snapshot,
                    vacancy.city,
                    vacancy.state,
                ],
            )
        ).lower()

        # Subject & Specialization Match
        if specialization and (
            specialization in haystack
            or any(w in haystack for w in specialization.split() if len(w) > 3)
        ):
            score += 15
            reasons.append("Matches your specialization")
        elif research and any(w in haystack for w in research.split() if len(w) > 4):
            score += 10
            reasons.append("Matches your research interests")

        # Department Match
        for dept in department_names:
            if dept and dept.lower() in haystack:
                score += 12
                reasons.append(f"In your department ({dept})")
                break

        # Highest Qualification Match
        if qualification:
            if (
                "phd" in qualification
                or "ph.d" in qualification
                or "doctorate" in qualification
            ):
                if "phd" in haystack or "ph.d" in haystack or "doctorate" in haystack:
                    score += 10
            elif any(q in haystack for q in qualification.split() if len(q) > 2):
                score += 8

        # Experience Match
        if vacancy.experience_min is not None:
            if exp_years >= vacancy.experience_min:
                score += 10
                reasons.append("Meets experience requirements")
            elif exp_years >= max(0, vacancy.experience_min - 2):
                score += 5
        else:
            score += 6

        # Location Match
        if preferred_locations:
            for loc in preferred_locations:
                if loc and loc in haystack:
                    score += 10
                    reasons.append("In your preferred location")
                    break

        # Certifications & Publications
        if profile.publications_count > 0:
            score += 4
            
        # Parsed Resume Skills Match
        if parsed_skills:
            matched_skills = [s for s in parsed_skills if s in haystack]
            if matched_skills:
                # Add up to 10 points for matching skills
                score += min(10, len(matched_skills) * 2)
                reasons.append("Matches skills in your CV")

        final_score = min(98, max(40, score))
        explanation = ", ".join(reasons[:2]) if reasons else "Good baseline match for your profile"
        return final_score, explanation
