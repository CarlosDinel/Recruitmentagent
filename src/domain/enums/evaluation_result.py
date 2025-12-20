"""Evaluation Result Enum"""

from enum import Enum


class EvaluationResult(str, Enum):
    """Result of candidate evaluation."""
    
    SUITABLE = "suitable"
    MAYBE = "maybe"
    UNSUITABLE = "unsuitable"
    NEEDS_MORE_INFO = "needs_more_info"
    
    def to_candidate_status(self):
        """Convert evaluation result to candidate status."""
        from .candidate_status import CandidateStatus
        
        mapping = {
            self.SUITABLE: CandidateStatus.SUITABLE,
            self.MAYBE: CandidateStatus.MAYBE,
            self.UNSUITABLE: CandidateStatus.UNSUITABLE,
            self.NEEDS_MORE_INFO: CandidateStatus.EVALUATING,
        }
        return mapping[self]
    
    def should_enrich(self) -> bool:
        """Check if candidate should be enriched."""
        return self in [self.SUITABLE, self.MAYBE]
