"""Domain Repository Interfaces"""

from .candidate_repository import CandidateRepository
from .project_repository import ProjectRepository
from .campaign_repository import CampaignRepository

__all__ = [
    'CandidateRepository',
    'ProjectRepository',
    'CampaignRepository',
]
