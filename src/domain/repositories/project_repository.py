"""Project Repository Interface"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities import Project
from ..value_objects import ProjectId


class ProjectRepository(ABC):
    """
    Abstract repository interface for project persistence.
    Infrastructure layer will implement this interface.
    """
    
    @abstractmethod
    async def save(self, project: Project) -> ProjectId:
        """
        Save or update a project.
        
        Args:
            project: Project entity to save
            
        Returns:
            ProjectId of the saved project
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, project_id: ProjectId) -> Optional[Project]:
        """
        Find project by ID.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Project if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_all_active(self) -> List[Project]:
        """
        Find all active projects.
        
        Returns:
            List of active projects
        """
        pass
    
    @abstractmethod
    async def find_by_stage(self, stage: str) -> List[Project]:
        """
        Find projects by workflow stage.
        
        Args:
            stage: Workflow stage
            
        Returns:
            List of projects
        """
        pass
    
    @abstractmethod
    async def find_by_company(self, company: str) -> List[Project]:
        """
        Find projects by company name.
        
        Args:
            company: Company name
            
        Returns:
            List of projects
        """
        pass
    
    @abstractmethod
    async def delete(self, project_id: ProjectId) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, project_id: ProjectId) -> bool:
        """
        Check if project exists.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if project exists
        """
        pass
    
    @abstractmethod
    async def count_active(self) -> int:
        """
        Count active projects.
        
        Returns:
            Number of active projects
        """
        pass
