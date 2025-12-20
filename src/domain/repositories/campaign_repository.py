"""Campaign Repository Interface"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities import Campaign
from ..value_objects import ProjectId


class CampaignRepository(ABC):
    """
    Abstract repository interface for campaign persistence.
    Infrastructure layer will implement this interface.
    """
    
    @abstractmethod
    async def save(self, campaign: Campaign) -> str:
        """
        Save or update a campaign.
        
        Args:
            campaign: Campaign entity to save
            
        Returns:
            Campaign ID
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """
        Find campaign by ID.
        
        Args:
            campaign_id: Unique campaign identifier
            
        Returns:
            Campaign if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_project(self, project_id: ProjectId) -> List[Campaign]:
        """
        Find all campaigns for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of campaigns
        """
        pass
    
    @abstractmethod
    async def find_active_by_project(self, project_id: ProjectId) -> List[Campaign]:
        """
        Find active campaigns for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of active campaigns
        """
        pass
    
    @abstractmethod
    async def find_by_channel(self, channel: str) -> List[Campaign]:
        """
        Find campaigns by outreach channel.
        
        Args:
            channel: Outreach channel
            
        Returns:
            List of campaigns
        """
        pass
    
    @abstractmethod
    async def delete(self, campaign_id: str) -> bool:
        """
        Delete a campaign.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, campaign_id: str) -> bool:
        """
        Check if campaign exists.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            True if campaign exists
        """
        pass
