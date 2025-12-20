"""Candidate Matching Service - Domain Logic"""

from typing import List, Tuple
from ..entities import Candidate, Project
from ..value_objects import SkillSet


class CandidateMatchingService:
    """
    Domain service for matching candidates to projects.
    Pure business logic with no external dependencies.
    """
    
    @staticmethod
    def calculate_match_score(candidate: Candidate, project: Project) -> float:
        """
        Calculate overall match score between candidate and project.
        
        Args:
            candidate: Candidate to evaluate
            project: Project requirements
            
        Returns:
            Match score from 0.0 to 1.0
        """
        # Skill match (50% weight)
        skill_score = candidate.skills.match_score(project.skills_needed)
        skill_weight = 0.5
        
        # Experience match (30% weight)
        experience_score = CandidateMatchingService._calculate_experience_score(
            candidate.years_experience, 
            project.experience_required
        )
        experience_weight = 0.3
        
        # Location match (20% weight)
        location_score = CandidateMatchingService._calculate_location_score(
            candidate.location, 
            project.location
        )
        location_weight = 0.2
        
        # Weighted average
        total_score = (
            skill_score * skill_weight +
            experience_score * experience_weight +
            location_score * location_weight
        )
        
        return round(total_score, 3)
    
    @staticmethod
    def _calculate_experience_score(candidate_years: int | None, required_years: int | None) -> float:
        """Calculate experience match score."""
        if required_years is None:
            return 1.0  # No requirement, perfect match
        
        if candidate_years is None:
            return 0.5  # Unknown experience, neutral score
        
        if candidate_years >= required_years:
            # Meets or exceeds requirement
            return 1.0
        
        # Calculate partial match
        ratio = candidate_years / required_years
        
        if ratio >= 0.8:
            return 0.9
        elif ratio >= 0.6:
            return 0.7
        elif ratio >= 0.4:
            return 0.5
        else:
            return 0.3
    
    @staticmethod
    def _calculate_location_score(candidate_location: str | None, project_location: str | None) -> float:
        """Calculate location match score."""
        if project_location is None:
            return 1.0  # No location requirement
        
        if candidate_location is None:
            return 0.5  # Unknown location, neutral score
        
        # Normalize for comparison
        candidate_loc = candidate_location.strip().lower()
        project_loc = project_location.strip().lower()
        
        if candidate_loc == project_loc:
            return 1.0  # Exact match
        
        # Check if one contains the other (e.g., "Amsterdam" in "Amsterdam, Netherlands")
        if candidate_loc in project_loc or project_loc in candidate_loc:
            return 0.9
        
        # Check for country match
        common_countries = ['netherlands', 'nederland', 'germany', 'deutschland', 'belgium', 'belgië']
        candidate_country = next((c for c in common_countries if c in candidate_loc), None)
        project_country = next((c for c in common_countries if c in project_loc), None)
        
        if candidate_country and project_country and candidate_country == project_country:
            return 0.7  # Same country, different city
        
        return 0.3  # Different locations
    
    @staticmethod
    def rank_candidates(candidates: List[Candidate], project: Project) -> List[Tuple[Candidate, float]]:
        """
        Rank candidates by match score for a project.
        
        Args:
            candidates: List of candidates to rank
            project: Project requirements
            
        Returns:
            List of (candidate, score) tuples sorted by score descending
        """
        scored_candidates = [
            (candidate, CandidateMatchingService.calculate_match_score(candidate, project))
            for candidate in candidates
        ]
        
        # Sort by score descending
        return sorted(scored_candidates, key=lambda x: x[1], reverse=True)
    
    @staticmethod
    def filter_by_minimum_score(
        candidates: List[Candidate], 
        project: Project, 
        min_score: float = 0.5
    ) -> List[Candidate]:
        """
        Filter candidates by minimum match score.
        
        Args:
            candidates: List of candidates to filter
            project: Project requirements
            min_score: Minimum match score threshold
            
        Returns:
            List of candidates meeting minimum score
        """
        return [
            candidate 
            for candidate in candidates
            if CandidateMatchingService.calculate_match_score(candidate, project) >= min_score
        ]
    
    @staticmethod
    def get_top_candidates(
        candidates: List[Candidate], 
        project: Project, 
        top_n: int = 10
    ) -> List[Tuple[Candidate, float]]:
        """
        Get top N candidates by match score.
        
        Args:
            candidates: List of candidates
            project: Project requirements
            top_n: Number of top candidates to return
            
        Returns:
            List of top (candidate, score) tuples
        """
        ranked = CandidateMatchingService.rank_candidates(candidates, project)
        return ranked[:top_n]
