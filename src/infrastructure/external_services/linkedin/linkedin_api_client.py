"""LinkedIn API Client using Unipile API."""

import os
import logging
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LinkedInAPIClient:
    """Client for interacting with LinkedIn via Unipile API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize LinkedIn API client.
        
        Args:
            api_key: Unipile API key (defaults to LINKEDIN_API_KEY env var)
            account_id: LinkedIn account ID (defaults to LINKEDIN_ACCOUNT_ID env var)
            base_url: API base URL (defaults to LINKEDIN_BASE_URL env var)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.getenv('LINKEDIN_API_KEY')
        self.account_id = account_id or os.getenv('LINKEDIN_ACCOUNT_ID')
        self.base_url = base_url or os.getenv(
            'LINKEDIN_BASE_URL',
            'https://api4.unipile.com:13447/api/v1'
        )
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("LINKEDIN_API_KEY is required")
        if not self.account_id:
            raise ValueError("LINKEDIN_ACCOUNT_ID is required")
        
        logger.info(f"LinkedInAPIClient initialized with base_url: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "accept": "application/json",
            "X-API-KEY": self.api_key
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Request body data
            
        Returns:
            Response JSON data
            
        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=self.timeout
                    )
                elif method.upper() == 'POST':
                    response = requests.post(
                        url,
                        headers=headers,
                        params=params,
                        json=data,
                        timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"LinkedIn API request failed after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"LinkedIn API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
        
        raise RuntimeError("Request failed after all retries")
    
    def get_saved_searches(self) -> List[Dict[str, Any]]:
        """
        Get saved searches from LinkedIn.
        
        Returns:
            List of saved search objects
        """
        try:
            params = {
                "type": "SAVED_SEARCHES",
                "account_id": self.account_id
            }
            
            data = self._make_request('GET', 'linkedin/search/parameters', params=params)
            
            items = data.get('items', [])
            logger.info(f"Retrieved {len(items)} saved searches")
            return items
            
        except Exception as e:
            logger.error(f"Error fetching saved searches: {e}")
            return []
    
    def get_search_parameters(self, search_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get search parameters (saved searches or specific search).
        
        Args:
            search_id: Optional specific search ID
            
        Returns:
            List of search parameter objects
        """
        try:
            params = {
                "type": "SAVED_SEARCHES",
                "account_id": self.account_id
            }
            
            if search_id:
                params["search_id"] = search_id
            
            data = self._make_request('GET', 'linkedin/search/parameters', params=params)
            
            items = data.get('items', [])
            logger.info(f"Retrieved {len(items)} search parameters")
            return items
            
        except Exception as e:
            logger.error(f"Error fetching search parameters: {e}")
            return []
    
    def execute_saved_search(
        self,
        search_id: str,
        limit: int = 25,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a saved LinkedIn search to retrieve candidates.
        
        This is the RECOMMENDED approach for Unipile as it works reliably
        across all account types without needing Sales Navigator.
        
        Args:
            search_id: The ID of the saved search (from get_saved_searches())
            limit: Maximum number of results to return (default: 25, max: 100)
            cursor: Pagination cursor for next page
            
        Returns:
            Dict with 'data' (list of profiles), 'has_more', and 'next_cursor'
        """
        try:
            # Build request data
            request_data = {
                "account_id": self.account_id,
                "search_id": str(search_id),
                "limit": min(limit, 100)
            }
            
            if cursor:
                request_data["cursor"] = cursor
            
            # Execute the saved search
            data = self._make_request('POST', 'linkedin/search/execute', data=request_data)
            
            # Format response
            result = self._format_search_response(data)
            
            logger.info(f"Executed saved search {search_id}, got {len(result.get('data', []))} results")
            return result
            
        except Exception as e:
            logger.error(f"Error executing saved search {search_id}: {e}")
            return {"data": [], "has_more": False, "next_cursor": None}
    
    def get_user_profile(self, provider_public_id: str, linkedin_sections: str = "*") -> Dict[str, Any]:
        """
        Get full LinkedIn profile by public ID.
        
        According to Unipile API: GET /api/v1/users/{provider_public_id}
        
        Args:
            provider_public_id: LinkedIn profile public ID (e.g., 'julien-crepieux' from URL)
            linkedin_sections: Sections to retrieve (default: "*" for all)
        
        Returns:
            Full profile data
        """
        try:
            params = {
                "linkedin_sections": linkedin_sections,
                "account_id": self.account_id
            }
            
            data = self._make_request('GET', f'users/{provider_public_id}', params=params)
            logger.info(f"Retrieved profile for {provider_public_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching profile {provider_public_id}: {e}")
            return {}
    
    def search_people(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 25,
        cursor: Optional[str] = None,
        api_type: str = "classic"  # "classic", "sales_navigator", or "recruiter"
    ) -> Dict[str, Any]:
        """
        Search for people on LinkedIn using Unipile API.
        
        Unipile requires specific format:
        - "classic": Standard LinkedIn search (most accounts)
        - "sales_navigator": LinkedIn Sales Navigator (premium)
        - "recruiter": LinkedIn Recruiter (enterprise)
        
        Args:
            query: Search query string (used as keywords)
            location: Location filter
            company: Company filter
            title: Job title filter
            skills: List of skills to search for
            limit: Maximum results per page (max 100)
            cursor: Pagination cursor
            api_type: LinkedIn API type to use
        
        Returns:
            Search results with candidates and pagination info
        """
        try:
            # Build keywords from query and filters
            keywords_parts = []
            if query:
                keywords_parts.append(query)
            if title:
                keywords_parts.append(title)
            if skills:
                keywords_parts.extend(skills)
            
            keywords = " ".join(keywords_parts) if keywords_parts else None
            
            # Build request according to Unipile schema
            request_data = {
                "api": api_type,
                "category": "people"
            }
            
            # Add filters based on API type
            if keywords:
                request_data["keywords"] = keywords
            
            # Profile language (recommended)
            request_data["profile_language"] = ["en", "nl"]
            
            # Note: account_id goes in QUERY PARAMS, not body
            params = {
                "account_id": self.account_id,
                "limit": min(limit, 100)
            }
            
            if cursor:
                params["cursor"] = cursor
            
            try:
                # Make request with account_id in params
                response = self._make_request(
                    'POST', 
                    'linkedin/search', 
                    params=params,
                    data=request_data
                )
                return self._format_search_response(response)
                
            except Exception as e:
                logger.error(f"LinkedIn search failed with {api_type}: {e}")
                
                # Try fallback to classic if using sales_navigator
                if api_type == "sales_navigator":
                    logger.info("Retrying with 'classic' API...")
                    request_data["api"] = "classic"
                    response = self._make_request(
                        'POST',
                        'linkedin/search',
                        params=params,
                        data=request_data
                    )
                    return self._format_search_response(response)
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error searching LinkedIn: {e}")
            logger.info("💡 Tip: Use saved searches (execute_saved_search) or profile scraping instead")
            return {"data": [], "has_more": False, "next_cursor": None}
    
    def _format_search_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format search response to consistent structure."""
        items = data.get('data', data.get('items', data.get('results', [])))
        has_more = data.get('has_more', data.get('next_cursor') is not None)
        next_cursor = data.get('next_cursor', data.get('cursor'))
        
        result = {
            "data": items,
            "has_more": has_more,
            "next_cursor": next_cursor
        }
        
        logger.info(f"LinkedIn search returned {len(items)} results")
        return result
    
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
        try:
            data = {
                "account_id": self.account_id,
                "provider_id": provider_id
            }
            
            if message:
                data["message"] = message
            
            result = self._make_request('POST', 'linkedin/connection/request', data=data)
            
            logger.info(f"Connection request sent to {provider_id}")
            return {
                "status": "success",
                "provider_id": provider_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error sending connection request: {e}")
            return {
                "status": "error",
                "provider_id": provider_id,
                "error": str(e)
            }
    
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
        try:
            data = {
                "account_id": self.account_id,
                "provider_id": provider_id,
                "message": message
            }
            
            result = self._make_request('POST', 'linkedin/message', data=data)
            
            logger.info(f"Message sent to {provider_id}")
            return {
                "status": "success",
                "provider_id": provider_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {
                "status": "error",
                "provider_id": provider_id,
                "error": str(e)
            }
    
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
        try:
            data = {
                "account_id": self.account_id,
                "provider_id": provider_id,
                "subject": subject,
                "body": body
            }
            
            result = self._make_request('POST', 'linkedin/inmail', data=data)
            
            logger.info(f"InMail sent to {provider_id}")
            return {
                "status": "success",
                "provider_id": provider_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error sending InMail: {e}")
            return {
                "status": "error",
                "provider_id": provider_id,
                "error": str(e)
            }

