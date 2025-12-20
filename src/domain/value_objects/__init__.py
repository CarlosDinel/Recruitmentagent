"""Domain Value Objects - Immutable Business Values"""

from .candidate_id import CandidateId
from .project_id import ProjectId
from .skill_set import SkillSet
from .contact_info import ContactInfo
from .evaluation_score import EvaluationScore

__all__ = [
    'CandidateId',
    'ProjectId',
    'SkillSet',
    'ContactInfo',
    'EvaluationScore',
]
