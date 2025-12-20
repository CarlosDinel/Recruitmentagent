"""Candidate Status Enum"""

from enum import Enum


class CandidateStatus(str, Enum):
    """Status of a candidate in the recruitment pipeline."""
    
    # Initial States
    NEW = "new"
    IDENTIFIED = "identified"
    
    # Evaluation States
    EVALUATING = "evaluating"
    SUITABLE = "suitable"
    MAYBE = "maybe"
    UNSUITABLE = "unsuitable"
    
    # Enrichment States
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    
    # Outreach States
    PRIORITIZED = "prioritized"
    OUTREACH_PENDING = "outreach_pending"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    NOT_RESPONDED = "not_responded"
    
    # Interview States
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    
    # Final States
    OFFERED = "offered"
    HIRED = "hired"
    REJECTED = "rejected"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    
    def is_active(self) -> bool:
        """Check if candidate is still active in pipeline."""
        return self not in [
            self.REJECTED,
            self.DECLINED,
            self.WITHDRAWN,
            self.HIRED,
            self.UNSUITABLE
        ]
    
    def is_suitable_for_outreach(self) -> bool:
        """Check if candidate is suitable for outreach."""
        return self in [
            self.SUITABLE,
            self.MAYBE,
            self.ENRICHED,
            self.PRIORITIZED
        ]
