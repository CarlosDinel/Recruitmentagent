"""LinkedIn Service Implementation."""

from typing import List, Dict, Any, Optional
import logging

from .linkedin_api_client import LinkedInAPIClient

logger = logging.getLogger(__name__)


class LinkedInServiceImpl:
    """Implementation of LinkedIn service using Unipile API."""
    
    def __init__(self, api_client: Optional[LinkedInAPIClient] = None):
        """
        Initialize LinkedIn service.
        
        Args:
            api_client: Optional LinkedIn API client (creates default if not provided)
        """
        self.api_client = api_client or LinkedInAPIClient()
        logger.info("LinkedInServiceImpl initialized")
    
    def get_saved_searches(self) -> List[Dict[str, Any]]:
        """
        Get saved searches from LinkedIn.
        
        Returns:
            List of saved search objects
        """
        return self.api_client.get_saved_searches()
    
    def search_candidates(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 25,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for candidates on LinkedIn.
        
        Args:
            query: Search query string
            location: Location filter
            company: Company filter
            title: Job title filter
            skills: List of skills to search for
            limit: Maximum results per page
            cursor: Pagination cursor
            
        Returns:
            Search results with candidates and pagination info
        """
        return self.api_client.search_people(
            query=query,
            location=location,
            company=company,
            title=title,
            skills=skills,
            limit=limit,
            cursor=cursor
        )
    
    def send_connection_request(
        self,
        provider_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send LinkedIn connection request.
        
        Args:
            provider_id: LinkedIn user ID
            message: Optional personalized message
            
        Returns:
            Result dictionary with status
        """
        return self.api_client.send_connection_request(provider_id, message)
    
    def send_message(
        self,
        provider_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send LinkedIn direct message.
        
        Args:
            provider_id: LinkedIn user ID
            message: Message text
            
        Returns:
            Result dictionary with status
        """
        return self.api_client.send_message(provider_id, message)
    
    def send_inmail(
        self,
        provider_id: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Send LinkedIn InMail.
        
        Args:
            provider_id: LinkedIn user ID
            subject: InMail subject
            body: InMail body
            
        Returns:
            Result dictionary with status
        """
        return self.api_client.send_inmail(provider_id, subject, body)

