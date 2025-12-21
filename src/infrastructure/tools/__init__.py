"""
LangGraph Tools - Infrastructure Layer

This module contains LangGraph-compatible tools for the recruitment agent system.
All tools are decorated with @tool from langchain.tools to maintain compatibility
with LangGraph workflows.

IMPORTANT: These tools MUST remain as @tool decorated functions for LangGraph compatibility.
They are infrastructure implementations that can be used by LangGraph agents.

Architecture:
============

    Infrastructure Tools (LangGraph Compatible)
    ├── Database Tools (@tool decorated)
    ├── Sourcing Tools (@tool decorated)
    ├── Outreach Tools (@tool decorated)
    └── Project Tools (@tool decorated)

Usage:
======

    from src.infrastructure.tools import (
        create_project_tool,
        search_candidates_tool,
        linkedin_connection_request_tool
    )
    
    # Use in LangGraph agent
    tools = [create_project_tool, search_candidates_tool]

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

"""
LangGraph Tools - Infrastructure Layer

All tools are @tool decorated for LangGraph compatibility.
"""

from .langgraph_database_tools import (
    create_project_tool,
    get_projects_tool,
    save_candidate_tool,
    validate_project_structure_tool
)

from .langgraph_sourcing_tools import (
    search_candidates_tool,
    match_candidates_to_job_tool
)

from .langgraph_outreach_tools import (
    linkedin_connection_request_tool,
    linkedin_message_send_tool,
    linkedin_inmail_send_tool,
    send_outreach_email_tool
)

from .langgraph_project_tools import (
    get_linkedin_saved_searches_tool,
    get_projects_from_linkedin_api_tool,
    get_projects_from_mongodb_tool,
    get_all_projects_tool,
    convert_project_to_json_tool
)

__all__ = [
    # Database tools
    'create_project_tool',
    'get_projects_tool',
    'save_candidate_tool',
    'validate_project_structure_tool',
    # Sourcing tools
    'search_candidates_tool',
    'match_candidates_to_job_tool',
    # Outreach tools
    'linkedin_connection_request_tool',
    'linkedin_message_send_tool',
    'linkedin_inmail_send_tool',
    'send_outreach_email_tool',
    # Project tools
    'get_linkedin_saved_searches_tool',
    'get_projects_from_linkedin_api_tool',
    'get_projects_from_mongodb_tool',
    'get_all_projects_tool',
    'convert_project_to_json_tool',
]

