"""Candidate Evaluation Service - Domain Logic"""

from typing import Dict, Any
from ..entities import Candidate, Project
from ..value_objects import EvaluationScore, SkillSet
from ..enums import EvaluationResult


class CandidateEvaluationService:
    """
    Domain service for evaluating candidate suitability.
    Pure business logic with no external dependencies.
    """
    
    @staticmethod
    def evaluate_candidate(
        candidate: Candidate, 
        project: Project,
        evaluation_criteria: Dict[str, Any] = None
    ) -> EvaluationScore:
        """
        Evaluate a candidate against project requirements.
        
        Args:
            candidate: Candidate to evaluate
            project: Project requirements
            evaluation_criteria: Optional custom evaluation criteria
            
        Returns:
            EvaluationScore with detailed scoring
        """
        criteria = evaluation_criteria or {}
        
        # Calculate individual scores
        skill_score = CandidateEvaluationService._evaluate_skills(
            candidate.skills, 
            project.skills_needed
        )
        
        experience_score = CandidateEvaluationService._evaluate_experience(
            candidate.years_experience,
            project.experience_required
        )
        
        culture_fit_score = CandidateEvaluationService._evaluate_culture_fit(
            candidate,
            project,
            criteria.get('culture_criteria', {})
        )
        
        # Calculate overall score (weighted average)
        skill_weight = criteria.get('skill_weight', 0.5)
        experience_weight = criteria.get('experience_weight', 0.3)
        culture_weight = criteria.get('culture_weight', 0.2)
        
        overall = (
            skill_score * skill_weight +
            experience_score * experience_weight +
            (culture_fit_score or 0.7) * culture_weight  # Default culture score if None
        )
        
        # Generate reasoning
        reasoning = CandidateEvaluationService._generate_reasoning(
            candidate,
            project,
            skill_score,
            experience_score,
            culture_fit_score
        )
        
        return EvaluationScore(
            overall_score=round(overall, 3),
            skill_match_score=round(skill_score, 3),
            experience_score=round(experience_score, 3),
            culture_fit_score=round(culture_fit_score, 3) if culture_fit_score else None,
            reasoning=reasoning
        )
    
    @staticmethod
    def _evaluate_skills(candidate_skills: SkillSet, required_skills: SkillSet) -> float:
        """Evaluate skill match."""
        if not required_skills.skills:
            return 1.0  # No requirements
        
        return candidate_skills.match_score(required_skills)
    
    @staticmethod
    def _evaluate_experience(candidate_years: int | None, required_years: int | None) -> float:
        """Evaluate experience match."""
        if required_years is None or required_years == 0:
            return 1.0  # No requirement
        
        if candidate_years is None:
            return 0.5  # Unknown, neutral score
        
        if candidate_years >= required_years * 1.5:
            return 1.0  # Significantly exceeds
        elif candidate_years >= required_years:
            return 0.95  # Meets requirement
        elif candidate_years >= required_years * 0.8:
            return 0.75  # Close to requirement
        elif candidate_years >= required_years * 0.5:
            return 0.5  # Half the requirement
        else:
            return 0.3  # Below requirement
    
    @staticmethod
    def _evaluate_culture_fit(
        candidate: Candidate, 
        project: Project, 
        culture_criteria: Dict[str, Any]
    ) -> float | None:
        """Evaluate culture fit (optional)."""
        if not culture_criteria:
            return None  # Culture fit not evaluated
        
        # This is a placeholder - in reality, culture fit evaluation
        # would require additional candidate data and criteria
        
        # For now, return a default score
        return 0.7
    
    @staticmethod
    def _generate_reasoning(
        candidate: Candidate,
        project: Project,
        skill_score: float,
        experience_score: float,
        culture_fit_score: float | None
    ) -> str:
        """Generate human-readable evaluation reasoning."""
        reasons = []
        
        # Skill reasoning
        if skill_score >= 0.8:
            reasons.append("Strong skill match")
        elif skill_score >= 0.6:
            reasons.append("Good skill match")
        elif skill_score >= 0.4:
            reasons.append("Partial skill match")
        else:
            reasons.append("Limited skill match")
        
        # Experience reasoning
        if experience_score >= 0.9:
            reasons.append("extensive relevant experience")
        elif experience_score >= 0.7:
            reasons.append("sufficient experience")
        elif experience_score >= 0.5:
            reasons.append("some relevant experience")
        else:
            reasons.append("limited experience")
        
        # Specific skills
        matched_skills = candidate.skills.skills & project.skills_needed.skills
        if matched_skills:
            skill_list = ', '.join(sorted(list(matched_skills))[:3])
            reasons.append(f"matches key skills: {skill_list}")
        
        # Location
        if candidate.location and project.location:
            if candidate.location.lower() in project.location.lower() or project.location.lower() in candidate.location.lower():
                reasons.append(f"located in {candidate.location}")
        
        return "; ".join(reasons) + "."
    
    @staticmethod
    def classify_candidate(evaluation_score: EvaluationScore) -> EvaluationResult:
        """
        Classify candidate based on evaluation score.
        
        Args:
            evaluation_score: Evaluation score
            
        Returns:
            EvaluationResult classification
        """
        return evaluation_score.to_evaluation_result()
    
    @staticmethod
    def should_enrich_profile(evaluation_score: EvaluationScore) -> bool:
        """
        Determine if candidate profile should be enriched.
        
        Args:
            evaluation_score: Evaluation score
            
        Returns:
            True if profile should be enriched
        """
        result = CandidateEvaluationService.classify_candidate(evaluation_score)
        return result.should_enrich()
