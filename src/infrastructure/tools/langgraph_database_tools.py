"""
LangGraph Database Tools - Infrastructure Layer

This module contains LangGraph-compatible database tools decorated with @tool.
These tools are used by LangGraph agents and must remain as @tool decorated functions.

IMPORTANT: These tools MUST remain as @tool decorated for LangGraph compatibility.
They are infrastructure implementations that wrap repository operations for LangGraph use.

Architecture:
============

    LangGraph Tools (Infrastructure)
    ├── Use Repository Interfaces (from domain)
    ├── Convert between LangGraph format and Domain entities
    └── Maintain @tool decorators for LangGraph compatibility

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

from typing import List, Dict, Any, Optional
from langchain.tools import tool
from datetime import datetime
import logging

# Import repository implementations (infrastructure)
try:
    from ...infrastructure.persistence.mongodb.mongodb_project_repository import MongoDBProjectRepository
    from ...infrastructure.persistence.mongodb.mongodb_candidate_repository import MongoDBCandidateRepository
except ImportError:
    MongoDBProjectRepository = None
    MongoDBCandidateRepository = None

# Import domain entities for conversion
try:
    from ...domain.entities.project import Project
    from ...domain.entities.candidate import Candidate
    from ...domain.value_objects.project_id import ProjectId
    from ...domain.value_objects.candidate_id import CandidateId
    from ...domain.value_objects.skill_set import SkillSet
    from ...domain.value_objects.contact_info import ContactInfo
    from ...domain.enums.workflow_stage import WorkflowStage
    from ...domain.enums.candidate_status import CandidateStatus
except ImportError:
    # Fallback if domain not available
    pass

logger = logging.getLogger(__name__)


# Initialize repositories (singleton pattern for LangGraph tools)
_project_repo = None
_candidate_repo = None


def _get_project_repository():
    """Get or create project repository instance."""
    global _project_repo
    if _project_repo is None and MongoDBProjectRepository:
        _project_repo = MongoDBProjectRepository()
    return _project_repo


def _get_candidate_repository():
    """Get or create candidate repository instance."""
    global _candidate_repo
    if _candidate_repo is None and MongoDBCandidateRepository:
        _candidate_repo = MongoDBCandidateRepository()
    return _candidate_repo


@tool
def create_project_tool(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new project in the database (LangGraph tool).
    
    This tool is compatible with LangGraph and wraps the repository operation.
    It converts between LangGraph format (dict) and domain entities.
    
    Args:
        project_data: Dictionary containing project information:
            - title: Project title (required)
            - project_id: Unique project identifier (required)
            - company: Company name (required)
            - description: Project description
            - skills_needed: List of required skills
            - location: Job location
            - target_candidate_count: Target number of candidates
    
    Returns:
        Dictionary with success status and project_id
    """
    try:
        repo = _get_project_repository()
        if not repo:
            # Fallback to old implementation if repository not available
            from tools.database_agent_tools import DatabaseTools
            db_tools = DatabaseTools()
            return db_tools.create_project.invoke({"project_data": project_data})
        
        # Convert dict to domain entity
        from ...domain.value_objects.project_id import ProjectId
        from ...domain.value_objects.skill_set import SkillSet
        from ...domain.enums.workflow_stage import WorkflowStage
        
        project = Project(
            id=ProjectId(project_data.get("project_id", f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}")),
            title=project_data["title"],
            company=project_data["company"],
            description=project_data.get("description", ""),
            requirements=project_data.get("description", ""),
            skills_needed=SkillSet(project_data.get("skills_needed", [])),
            stage=WorkflowStage.REQUEST_RECEIVED,
            location=project_data.get("location"),
            experience_required=project_data.get("experience_required"),
            target_candidate_count=project_data.get("target_candidate_count", 50)
        )
        
        # Save via repository (async, but tool is sync - will need adapter)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            project_id = loop.run_until_complete(repo.save(project))
        except RuntimeError:
            # No event loop, create new one
            project_id = asyncio.run(repo.save(project))
        
        return {
            "success": True,
            "project_id": str(project_id),
            "action": "created",
            "message": "Project created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create project"
        }


@tool
def get_projects_tool(query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get projects from database (LangGraph tool).
    
    Args:
        query: Optional MongoDB query for filtering
    
    Returns:
        List of project dictionaries
    """
    try:
        repo = _get_project_repository()
        if not repo:
            # Fallback to old implementation
            from tools.database_agent_tools import DatabaseTools
            db_tools = DatabaseTools()
            result = db_tools.get_projects.invoke({"query": query})
            return result.get("projects", []) if isinstance(result, dict) else result
        
        # Get projects via repository
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            projects = loop.run_until_complete(repo.find_all_active())
        except RuntimeError:
            projects = asyncio.run(repo.find_all_active())
        
        # Convert entities to dicts
        return [p.to_dict() for p in projects]
        
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return []


@tool
def save_candidate_tool(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save candidate to database (LangGraph tool).
    
    Args:
        candidate_data: Dictionary containing candidate information
    
    Returns:
        Dictionary with success status and candidate_id
    """
    try:
        repo = _get_candidate_repository()
        if not repo:
            # Fallback to old implementation
            from tools.database_agent_tools import DatabaseTools
            db_tools = DatabaseTools()
            return db_tools.save_candidate.invoke({"candidate_data": candidate_data})
        
        # Convert dict to domain entity
        from ...domain.value_objects.candidate_id import CandidateId
        from ...domain.value_objects.skill_set import SkillSet
        from ...domain.value_objects.contact_info import ContactInfo
        from ...domain.enums.candidate_status import CandidateStatus
        
        candidate_id = CandidateId.from_linkedin_url(
            candidate_data.get("linkedin_url", "")
        ) if candidate_data.get("linkedin_url") else CandidateId(str(candidate_data.get("candidate_id", "")))
        
        contact_info = ContactInfo(
            email=candidate_data.get("email"),
            phone=candidate_data.get("phone"),
            linkedin_url=candidate_data.get("linkedin_url")
        )
        
        candidate = Candidate(
            id=candidate_id,
            name=candidate_data.get("name", "Unknown"),
            current_position=candidate_data.get("title"),
            current_company=candidate_data.get("company"),
            location=candidate_data.get("location"),
            contact_info=contact_info,
            skills=SkillSet(candidate_data.get("skills", [])),
            years_experience=candidate_data.get("experience_years"),
            education=candidate_data.get("education"),
            status=CandidateStatus.NEW,
            profile_data=candidate_data
        )
        
        # Save via repository
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            saved_id = loop.run_until_complete(repo.save(candidate))
        except RuntimeError:
            saved_id = asyncio.run(repo.save(candidate))
        
        return {
            "success": True,
            "candidate_id": str(saved_id),
            "action": "created",
            "message": "Candidate saved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error saving candidate: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to save candidate"
        }


@tool
def validate_project_structure_tool(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate project structure without saving (LangGraph tool).
    
    Args:
        project_data: Dictionary containing project information
    
    Returns:
        Dictionary with validation results
    """
    try:
        # Use domain entity validation
        from ...domain.entities.project import Project
        from ...domain.value_objects.project_id import ProjectId
        from ...domain.value_objects.skill_set import SkillSet
        from ...domain.enums.workflow_stage import WorkflowStage
        
        project = Project(
            id=ProjectId(project_data.get("project_id", "temp")),
            title=project_data.get("title", ""),
            company=project_data.get("company", ""),
            description=project_data.get("description", ""),
            requirements=project_data.get("description", ""),
            skills_needed=SkillSet(project_data.get("skills_needed", [])),
            stage=WorkflowStage.REQUEST_RECEIVED,
            location=project_data.get("location"),
            experience_required=project_data.get("experience_required"),
            target_candidate_count=project_data.get("target_candidate_count", 50)
        )
        
        return {
            "success": True,
            "valid": True,
            "structured_project": project.to_dict(),
            "message": "Project structure is valid"
        }
        
    except ValueError as e:
        return {
            "success": False,
            "valid": False,
            "error": str(e),
            "message": "Project validation failed"
        }
    except Exception as e:
        logger.error(f"Error validating project: {e}")
        return {
            "success": False,
            "valid": False,
            "error": str(e),
            "message": "Unexpected validation error"
        }

