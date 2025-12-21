"""
LangGraph Project Tools - Infrastructure Layer

This module contains LangGraph-compatible project tools decorated with @tool.
These tools are used by LangGraph agents for project management.

IMPORTANT: These tools MUST remain as @tool decorated for LangGraph compatibility.

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

from typing import List, Dict, Any, Optional
from langchain.tools import tool
import logging
import json
from datetime import datetime

# Import infrastructure services
try:
    from ...infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
    from ...infrastructure.persistence.mongodb.mongodb_project_repository import MongoDBProjectRepository
except ImportError:
    LinkedInServiceImpl = None
    MongoDBProjectRepository = None

logger = logging.getLogger(__name__)


# Initialize services (singleton pattern)
_linkedin_service = None
_project_repo = None


def _get_linkedin_service():
    """Get or create LinkedIn service instance."""
    global _linkedin_service
    if _linkedin_service is None and LinkedInServiceImpl:
        _linkedin_service = LinkedInServiceImpl()
    return _linkedin_service


def _get_project_repository():
    """Get or create project repository instance."""
    global _project_repo
    if _project_repo is None and MongoDBProjectRepository:
        _project_repo = MongoDBProjectRepository()
    return _project_repo


@tool
def get_linkedin_saved_searches_tool() -> List[Dict[str, Any]]:
    """
    Get saved searches from LinkedIn API (LangGraph tool).
    
    Returns:
        List of LinkedIn saved searches with their parameters
    """
    try:
        logger.info("🔍 Fetching saved searches from LinkedIn API...")
        
        linkedin_service = _get_linkedin_service()
        if linkedin_service:
            saved_searches = linkedin_service.get_saved_searches()
            return saved_searches
        else:
            # Fallback to old implementation
            from tools.get_projects import get_linkedin_saved_searches
            return get_linkedin_saved_searches.invoke({})
            
    except Exception as e:
        logger.error(f"Error fetching saved searches: {e}")
        return []


@tool
def get_projects_from_linkedin_api_tool() -> List[Dict[str, Any]]:
    """
    Get projects from LinkedIn API (LangGraph tool).
    
    Returns:
        List of project dictionaries from LinkedIn
    """
    try:
        logger.info("🔍 Fetching projects from LinkedIn API...")
        
        linkedin_service = _get_linkedin_service()
        if linkedin_service:
            saved_searches = linkedin_service.get_saved_searches()
            # Convert saved searches to project format
            projects = []
            for search in saved_searches:
                project = {
                    "project_id": search.get("id", ""),
                    "title": search.get("title", "Untitled Search"),
                    "source": "linkedin_api",
                    "created_at": search.get("created_at"),
                    "updated_at": search.get("updated_at"),
                    "linkedin_search_parameters": search.get("additional_data", {})
                }
                projects.append(project)
            return projects
        else:
            # Fallback to old implementation
            from tools.get_projects import get_projects_from_linkedin_api
            return get_projects_from_linkedin_api.invoke({})
            
    except Exception as e:
        logger.error(f"Error fetching projects from LinkedIn: {e}")
        return []


@tool
def get_projects_from_mongodb_tool() -> List[Dict[str, Any]]:
    """
    Get projects from MongoDB (LangGraph tool).
    
    Returns:
        List of project dictionaries from MongoDB
    """
    try:
        logger.info("🔍 Fetching projects from MongoDB...")
        
        repo = _get_project_repository()
        if repo:
            import asyncio
            
            # Handle async call from sync context
            projects = None
            try:
                # Check if there's a running event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, can't use asyncio.run()
                    # Fall back to old implementation
                    logger.warning("Cannot run async in running event loop. Using fallback.")
                    from tools.get_projects import get_projects_from_mongodb
                    return get_projects_from_mongodb.invoke({})
                except RuntimeError:
                    # No running loop, try to get/create one
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Loop exists and is running, use fallback
                            logger.warning("Event loop is running. Using fallback.")
                            from tools.get_projects import get_projects_from_mongodb
                            return get_projects_from_mongodb.invoke({})
                        else:
                            # Loop exists but not running, use it
                            projects = loop.run_until_complete(repo.find_all_active())
                    except RuntimeError:
                        # No event loop, create new one
                        projects = asyncio.run(repo.find_all_active())
            except Exception as e:
                logger.error(f"Error in async handling: {e}")
                # Fallback to old implementation
                from tools.get_projects import get_projects_from_mongodb
                return get_projects_from_mongodb.invoke({})
            
            if projects is not None:
                return [p.to_dict() for p in projects]
            else:
                # Fallback if projects is None
                from tools.get_projects import get_projects_from_mongodb
                return get_projects_from_mongodb.invoke({})
        else:
            # Fallback to old implementation
            from tools.get_projects import get_projects_from_mongodb
            return get_projects_from_mongodb.invoke({})
            
    except Exception as e:
        logger.error(f"Error fetching projects from MongoDB: {e}")
        return []


@tool
def get_all_projects_tool(
    use_mongodb: bool = False,
    fallback: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all projects with fallback logic (LangGraph tool).
    
    Args:
        use_mongodb: If True, try MongoDB first, else try LinkedIn API first
        fallback: If True, try secondary source if primary fails
    
    Returns:
        List of project dictionaries
    """
    try:
        primary_source = "MongoDB" if use_mongodb else "LinkedIn API"
        secondary_source = "LinkedIn API" if use_mongodb else "MongoDB"
        
        logger.info(f"🔄 Attempting to fetch projects from {primary_source}...")
        
        # Try primary source
        if use_mongodb:
            projects = get_projects_from_mongodb_tool.invoke({})
        else:
            projects = get_projects_from_linkedin_api_tool.invoke({})
        
        # If primary failed and fallback enabled, try secondary
        if not projects and fallback:
            logger.info(f"⚠️ {primary_source} returned no results. Trying {secondary_source}...")
            if use_mongodb:
                projects = get_projects_from_linkedin_api_tool.invoke({})
            else:
                projects = get_projects_from_mongodb_tool.invoke({})
        
        # Remove duplicates
        if projects:
            seen_ids = set()
            unique_projects = []
            for project in projects:
                project_id = project.get("project_id") or project.get("_id") or project.get("id", "")
                if project_id and project_id not in seen_ids:
                    seen_ids.add(project_id)
                    unique_projects.append(project)
            projects = unique_projects
        
        logger.info(f"✅ Final result: {len(projects)} unique projects available")
        return projects
        
    except Exception as e:
        logger.error(f"Error getting all projects: {e}")
        return []


@tool
def convert_project_to_json_tool(project_data: Dict[str, Any]) -> str:
    """
    Convert project data to JSON format (LangGraph tool).
    
    Args:
        project_data: Dictionary containing project information
    
    Returns:
        JSON string representation of project
    """
    try:
        return json.dumps(project_data, default=str)
    except Exception as e:
        logger.error(f"Error converting project to JSON: {e}")
        return json.dumps({"error": str(e)})

