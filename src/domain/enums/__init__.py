"""Domain Enums - Business State Definitions"""

from .candidate_status import CandidateStatus
from .outreach_channel import OutreachChannel
from .evaluation_result import EvaluationResult
from .workflow_stage import WorkflowStage

__all__ = [
    'CandidateStatus',
    'OutreachChannel',
    'EvaluationResult',
    'WorkflowStage',
]
