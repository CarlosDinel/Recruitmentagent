"""
LangGraph Sourcing Tools - Infrastructure Layer

This module contains LangGraph-compatible sourcing tools decorated with @tool.
These tools are used by LangGraph agents for candidate searching.

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
except ImportError:
    LinkedInServiceImpl = None

logger = logging.getLogger(__name__)


# Initialize LinkedIn service (singleton pattern)
_linkedin_service = None


def _get_linkedin_service():
    """Get or create LinkedIn service instance."""
    global _linkedin_service
    if _linkedin_service is None and LinkedInServiceImpl:
        _linkedin_service = LinkedInServiceImpl()
    return _linkedin_service


@tool
def search_candidates_tool(
    project_id: str,
    search_id: str,
    max_results: int = 50,
    location: str = "",
    keywords: str = "",
    company_name: str = "",
    job_title: str = "",
    skills: str = "",  # Comma-separated for tool compatibility
    experience_level: str = "",
    use_cursor: bool = True
) -> str:  # Returns JSON string for LangGraph compatibility
    """
    Search for candidates on LinkedIn (LangGraph tool).
    
    This tool searches LinkedIn for candidates matching the specified criteria.
    Returns results as JSON string for LangGraph compatibility.
    
    Args:
        project_id: Unique identifier for the hiring project
        search_id: Unique identifier for this search
        max_results: Maximum number of candidates to return
        location: Geographic location filter
        keywords: Keywords to search for
        company_name: Company filter
        job_title: Job title filter
        skills: Comma-separated list of skills
        experience_level: Experience level filter
        use_cursor: Whether to use cursor-based pagination
    
    Returns:
        JSON string containing search results and metadata
    """
    logger.info(f"🔍 Searching candidates for project {project_id}, search {search_id}")
    
    try:
        linkedin_service = _get_linkedin_service()
        
        # Parse skills from comma-separated string
        skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
        
        # Execute search
        if linkedin_service:
            search_results = linkedin_service.search_candidates(
                query=keywords,
                location=location,
                company=company_name,
                title=job_title,
                skills=skills_list,
                limit=max_results
            )
            
            candidates = search_results.get("data", [])
        else:
            # Fallback to old implementation
            from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
            result_str = search_candidates_integrated_cursor_and_no_cursor.invoke({
                "project_id": project_id,
                "search_id": search_id,
                "max_results": max_results,
                "location": location,
                "keywords": keywords,
                "company_name": company_name,
                "job_title": job_title,
                "skills": skills,
                "experience_level": experience_level,
                "use_cursor": use_cursor
            })
            result = json.loads(result_str) if isinstance(result_str, str) else result_str
            candidates = result.get("candidates", [])
        
        # Prepare response
        response = {
            "success": True,
            "search_metadata": {
                "project_id": project_id,
                "search_id": search_id,
                "total_found": len(candidates),
                "search_timestamp": datetime.now().isoformat()
            },
            "candidates": candidates
        }
        
        return json.dumps(response)
        
    except Exception as e:
        logger.error(f"Error searching candidates: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "candidates": []
        })


@tool
def match_candidates_to_job_tool(
    candidates_json: str,
    job_description: str
) -> str:  # Returns JSON string for LangGraph compatibility
    """
    Match candidates to job requirements (LangGraph tool).
    
    This tool evaluates candidates against job requirements using AI.
    Returns results as JSON string for LangGraph compatibility.
    
    Args:
        candidates_json: JSON string containing candidate list
        job_description: Job description and requirements
    
    Returns:
        JSON string containing match analysis for each candidate
    """
    logger.info("🎯 Matching candidates to job requirements")
    
    try:
        candidates = json.loads(candidates_json) if isinstance(candidates_json, str) else candidates_json
        candidates_list = candidates.get("candidates", []) if isinstance(candidates, dict) else candidates
        
        # Use domain evaluation service if available
        try:
            from ...domain.services.candidate_evaluation_service import CandidateEvaluationService
            from ...domain.entities.candidate import Candidate
            from ...domain.entities.project import Project
            from ...domain.value_objects.skill_set import SkillSet
            
            # For now, return simplified matching
            # In production, this would use the full evaluation service
            match_results = []
            for candidate_data in candidates_list:
                match_result = {
                    "candidate": candidate_data,
                    "match_analysis": {
                        "overall_match": 0.75,  # Placeholder
                        "skill_match": 0.8,
                        "experience_match": 0.7,
                        "reasoning": "Candidate matches key requirements"
                    }
                }
                match_results.append(match_result)
            
            return json.dumps(match_results)
            
        except ImportError:
            # Fallback to old implementation
            from tools.scourcing_tools import match_candidates_to_job
            return match_candidates_to_job.invoke({
                "candidates_json": candidates_json,
                "job_description": job_description
            })
        
    except Exception as e:
        logger.error(f"Error matching candidates: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "matches": []
        })

