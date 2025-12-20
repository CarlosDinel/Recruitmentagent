"""Candidate Repository Interface"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..entities import Candidate
from ..value_objects import CandidateId, ProjectId


class CandidateRepository(ABC):
    """
    Abstract repository interface for candidate persistence.
    Infrastructure layer will implement this interface.
    """
    
    @abstractmethod
    async def save(self, candidate: Candidate) -> CandidateId:
        """
        Save or update a candidate.
        
        Args:
            candidate: Candidate entity to save
            
        Returns:
            CandidateId of the saved candidate
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, candidate_id: CandidateId) -> Optional[Candidate]:
        """
        Find candidate by ID.
        
        Args:
            candidate_id: Unique candidate identifier
            
        Returns:
            Candidate if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_linkedin_url(self, linkedin_url: str) -> Optional[Candidate]:
        """
        Find candidate by LinkedIn URL (for deduplication).
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Candidate if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_project(self, project_id: ProjectId) -> List[Candidate]:
        """
        Find all candidates for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of candidates
        """
        pass
    
    @abstractmethod
    async def find_by_status(self, status: str, project_id: Optional[ProjectId] = None) -> List[Candidate]:
        """
        Find candidates by status, optionally filtered by project.
        
        Args:
            status: Candidate status
            project_id: Optional project filter
            
        Returns:
            List of candidates
        """
        pass
    
    @abstractmethod
    async def search_by_skills(self, skills: List[str], min_match: float = 0.5) -> List[Candidate]:
        """
        Search candidates by skills.
        
        Args:
            skills: Required skills
            min_match: Minimum match score (0.0 to 1.0)
            
        Returns:
            List of matching candidates
        """
        pass
    
    @abstractmethod
    async def delete(self, candidate_id: CandidateId) -> bool:
        """
        Delete a candidate.
        
        Args:
            candidate_id: Candidate identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists_by_linkedin_url(self, linkedin_url: str) -> bool:
        """
        Check if candidate exists by LinkedIn URL.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            True if candidate exists
        """
        pass
    
    @abstractmethod
    async def count_by_project(self, project_id: ProjectId, status: Optional[str] = None) -> int:
        """
        Count candidates for a project, optionally filtered by status.
        
        Args:
            project_id: Project identifier
            status: Optional status filter
            
        Returns:
            Number of candidates
        """
        pass
    
    @abstractmethod
    async def batch_save(self, candidates: List[Candidate]) -> List[CandidateId]:
        """
        Save multiple candidates in batch.
        
        Args:
            candidates: List of candidates to save
            
        Returns:
            List of candidate IDs
        """
        pass
