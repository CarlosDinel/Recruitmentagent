"""
Domain Layer - Pure Business Logic
No external dependencies allowed in this layer
"""

from .entities import Candidate, Project, Campaign, OutreachMessage, RecruitmentRequest
from .value_objects import CandidateId, ProjectId, SkillSet, ContactInfo, EvaluationScore
from .enums import CandidateStatus, OutreachChannel, EvaluationResult, WorkflowStage

__all__ = [
    # Entities
    'Candidate',
    'Project', 
    'Campaign',
    'OutreachMessage',
    'RecruitmentRequest',
    
    # Value Objects
    'CandidateId',
    'ProjectId',
    'SkillSet',
    'ContactInfo',
    'EvaluationScore',
    
    # Enums
    'CandidateStatus',
    'OutreachChannel',
    'EvaluationResult',
    'WorkflowStage',
]
