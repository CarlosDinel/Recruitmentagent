"""Workflow Stage Enum"""

from enum import Enum


class WorkflowStage(str, Enum):
    """Stages in the recruitment workflow."""
    
    # Recruitment Executive Stages
    REQUEST_RECEIVED = "request_received"
    REQUEST_ANALYZED = "request_analyzed"
    PROJECT_CREATED = "project_created"
    
    # Sourcing Manager Stages
    SOURCING_STARTED = "sourcing_started"
    SEARCHING = "searching"
    EVALUATING = "evaluating"
    ENRICHING = "enriching"
    OPTIMIZING = "optimizing"
    SOURCING_COMPLETED = "sourcing_completed"
    
    # Outreach Manager Stages
    OUTREACH_STARTED = "outreach_started"
    PRIORITIZING = "prioritizing"
    MESSAGE_GENERATION = "message_generation"
    OUTREACH_EXECUTION = "outreach_execution"
    TRACKING = "tracking"
    OPTIMIZATION = "optimization"
    OUTREACH_COMPLETED = "outreach_completed"
    
    # Interview & Hiring Stages
    INTERVIEW_SCHEDULING = "interview_scheduling"
    INTERVIEWING = "interviewing"
    OFFER_PREPARATION = "offer_preparation"
    HIRING = "hiring"
    
    # Final Stages
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def is_sourcing_stage(self) -> bool:
        """Check if this is a sourcing stage."""
        return self in [
            self.SOURCING_STARTED,
            self.SEARCHING,
            self.EVALUATING,
            self.ENRICHING,
            self.OPTIMIZING,
            self.SOURCING_COMPLETED
        ]
    
    def is_outreach_stage(self) -> bool:
        """Check if this is an outreach stage."""
        return self in [
            self.OUTREACH_STARTED,
            self.PRIORITIZING,
            self.MESSAGE_GENERATION,
            self.OUTREACH_EXECUTION,
            self.TRACKING,
            self.OPTIMIZATION,
            self.OUTREACH_COMPLETED
        ]
    
    def is_terminal(self) -> bool:
        """Check if this is a terminal stage."""
        return self in [self.COMPLETED, self.FAILED, self.CANCELLED]
