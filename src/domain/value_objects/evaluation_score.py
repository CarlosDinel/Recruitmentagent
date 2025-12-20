"""Evaluation Score Value Object"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class EvaluationScore:
    """Immutable evaluation score for a candidate."""
    
    overall_score: float
    skill_match_score: float
    experience_score: float
    culture_fit_score: Optional[float]
    reasoning: str
    
    def __post_init__(self):
        """Validate evaluation scores."""
        self._validate_score(self.overall_score, "overall_score")
        self._validate_score(self.skill_match_score, "skill_match_score")
        self._validate_score(self.experience_score, "experience_score")
        
        if self.culture_fit_score is not None:
            self._validate_score(self.culture_fit_score, "culture_fit_score")
        
        if not self.reasoning or not self.reasoning.strip():
            raise ValueError("Reasoning cannot be empty")
    
    @staticmethod
    def _validate_score(score: float, field_name: str) -> None:
        """Validate score is between 0.0 and 1.0."""
        if not isinstance(score, (int, float)):
            raise ValueError(f"{field_name} must be a number")
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0, got {score}")
    
    def is_suitable(self, threshold: float = 0.7) -> bool:
        """Check if candidate is suitable based on overall score."""
        return self.overall_score >= threshold
    
    def is_maybe(self, min_threshold: float = 0.5, max_threshold: float = 0.7) -> bool:
        """Check if candidate is maybe suitable."""
        return min_threshold <= self.overall_score < max_threshold
    
    def is_unsuitable(self, threshold: float = 0.5) -> bool:
        """Check if candidate is unsuitable."""
        return self.overall_score < threshold
    
    def to_evaluation_result(self, 
                            suitable_threshold: float = 0.7,
                            maybe_threshold: float = 0.5):
        """Convert score to evaluation result."""
        from ..enums import EvaluationResult
        
        if self.is_suitable(suitable_threshold):
            return EvaluationResult.SUITABLE
        elif self.is_maybe(maybe_threshold, suitable_threshold):
            return EvaluationResult.MAYBE
        else:
            return EvaluationResult.UNSUITABLE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'overall_score': self.overall_score,
            'skill_match_score': self.skill_match_score,
            'experience_score': self.experience_score,
            'culture_fit_score': self.culture_fit_score,
            'reasoning': self.reasoning
        }
    
    def __str__(self) -> str:
        return f"EvaluationScore(overall={self.overall_score:.2f}, skills={self.skill_match_score:.2f}, experience={self.experience_score:.2f})"
