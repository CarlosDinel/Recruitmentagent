"""This agent is a sub-agent of the scourcing_manager.py agent. 
It is responsible for searching and identifying potential candidates for job openings based on specific criteria provided by the sourcing manager.
The agent utilizes various tools and APIs to search on LinkedIn to find and ingest candidate profiles that eventually will be stored by the database_agent.py. 
Additionally, the agent can filter and rank candidates based on relevance to the job requirements, ensuring that only the most suitable profiles are considered for further evaluation.

"""

#  ---- Package imports ----
from typing import List, Annotated, Sequence, Dict, Any, Optional
import logging 
import json
from datetime import datetime

#  ---- Local imports ----
from agents.database_agent import DatabaseAgent
from tools.scourcing_tools import (
    search_candidates_integrated_cursor_and_no_cursor,
    LinkedIn_profile_scrape,
    match_candidates_to_job
)

# Set up logging
logger = logging.getLogger(__name__)

class CandidateSearchingAgentState:
    """State for the Candidate Searching Agent."""
    
    def __init__(self):
        # Input from Sourcing Manager
        self.project_id: str = ""
        self.search_id: str = ""
        self.naam_project: str = ""
        self.campaign_num: str = ""
        self.search_criteria: Dict[str, Any] = {}
        self.job_requirements: Optional[str] = None
        self.max_results: int = 50
        
        # Processing state
        self.current_step: str = "initialized"
        self.search_results: Dict[str, Any] = {}
        self.enriched_candidates: List[Dict[str, Any]] = []
        self.matched_candidates: List[Dict[str, Any]] = []
        
        # Output
        self.database_payload: Dict[str, Any] = {}
        self.sourcing_manager_summary: Dict[str, Any] = {}
        self.success: bool = False
        self.error_message: str = ""

class CandidateSearchingAgent:
    """
    Candidate Searching Agent - Specialized in LinkedIn candidate discovery.
    
    Role: LinkedIn candidate discovery and enrichment specialist
    Responsibilities:
    - Receive instructions only from Sourcing Manager
    - Search candidates based on projectid and searchid
    - Enrich candidate results with project metadata
    - Forward all results to Database Agent
    - Return candidate summaries to Sourcing Manager
    """
    
    def __init__(self):
        self.name = "Candidate Searching Agent"
        self.role = "LinkedIn candidate discovery and enrichment"
        
        # Available tools
        self.tools = [
            search_candidates_integrated_cursor_and_no_cursor,
            LinkedIn_profile_scrape,
            match_candidates_to_job
        ]
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing Sourcing Manager requests.
        
        Args:
            request: Dictionary containing:
                - projectid: Unique project identifier
                - searchid: Unique search identifier  
                - naam_project: Project name
                - campaign_num: Campaign number
                - search_criteria: Optional search parameters
                - job_requirements: Optional job description for matching
                - max_results: Optional maximum results (default: 50)
                
        Returns:
            Dictionary with results for Sourcing Manager and Database Agent
        """
        logger.info(f"🤖 {self.name} processing request for project {request.get('projectid', 'unknown')}")
        
        try:
            # Initialize state
            state = {
                "request": request,
                "current_step": "initialized",
                "search_results": {},
                "enriched_candidates": [],
                "matched_candidates": [],
                "database_payload": {},
                "sourcing_manager_summary": {},
                "success": False,
                "error_message": ""
            }
            
            # Execute workflow steps
            state = self._parse_sourcing_manager_request(state)
            if not state.get("success", True) and state.get("error_message"):
                return state
                
            state = self._search_candidates(state)
            if not state.get("success", True) and state.get("error_message"):
                return state
                
            state = self._enrich_candidates(state)
            if not state.get("success", True) and state.get("error_message"):
                return state
                
            state = self._match_candidates_optional(state)
            # Don't fail for matching errors
            
            state = self._prepare_database_payload(state)
            if not state.get("success", True) and state.get("error_message"):
                return state
                
            state = self._prepare_sourcing_summary(state)
            if not state.get("success", True) and state.get("error_message"):
                return state
                
            state = self._finalize_response(state)
            
            return state
            
        except Exception as e:
            logger.error(f"❌ {self.name} failed to process request: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "database_payload": {},
                "sourcing_manager_summary": {}
            }
    
    def _parse_sourcing_manager_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the incoming request from Sourcing Manager."""
        logger.info("📋 Parsing Sourcing Manager request...")
        
        request = state.get("request", {})
        
        # Extract required parameters
        project_id = request.get("projectid")
        search_id = request.get("searchid")
        naam_project = request.get("naam_project")
        campaign_num = request.get("campaign_num")
        
        # Validate required parameters
        if not all([project_id, search_id, naam_project, campaign_num]):
            error_msg = "Missing required parameters: projectid, searchid, naam_project, campaign_num"
            logger.error(f"❌ {error_msg}")
            state["success"] = False
            state["error_message"] = error_msg
            return state
        
        # Extract optional parameters
        search_criteria = request.get("search_criteria", {})
        job_requirements = request.get("job_requirements")
        max_results = request.get("max_results", 50)
        
        # Update state
        state.update({
            "project_id": project_id,
            "search_id": search_id,
            "naam_project": naam_project,
            "campaign_num": campaign_num,
            "search_criteria": search_criteria,
            "job_requirements": job_requirements,
            "max_results": max_results,
            "current_step": "request_parsed"
        })
        
        logger.info(f"✅ Request parsed: {project_id} - {naam_project}")
        return state
    
    def _search_candidates(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Search for candidates using the search tool."""
        logger.info("🔍 Searching for candidates...")
        
        try:
            # Extract search parameters
            search_criteria = state.get("search_criteria", {})
            
            # Prepare tool parameters
            tool_params = {
                "project_id": state["project_id"],
                "search_id": state["search_id"],
                "max_results": state["max_results"],
                "location": search_criteria.get("location", ""),
                "keywords": search_criteria.get("keywords", ""),
                "company_name": search_criteria.get("company_name", ""),
                "job_title": search_criteria.get("job_title", ""),
                "skills": self._format_skills_for_tool(search_criteria.get("skills", [])),
                "experience_level": search_criteria.get("experience_level", ""),
                "use_cursor": search_criteria.get("use_cursor", True)
            }
            
            # Call the search tool
            search_result_json = search_candidates_integrated_cursor_and_no_cursor.invoke(tool_params)
            search_results = json.loads(search_result_json)
            
            if not search_results.get("success", False):
                error_msg = f"Search failed: {search_results.get('error', 'Unknown error')}"
                logger.error(f"❌ {error_msg}")
                state["success"] = False
                state["error_message"] = error_msg
                return state
            
            state["search_results"] = search_results
            state["current_step"] = "candidates_found"
            
            candidates_count = len(search_results.get("candidates", []))
            logger.info(f"✅ Found {candidates_count} candidates")
            
            return state
            
        except Exception as e:
            error_msg = f"Candidate search failed: {e}"
            logger.error(f"❌ {error_msg}")
            state["success"] = False
            state["error_message"] = error_msg
            return state
    
    def _enrich_candidates(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich candidates with project metadata."""
        logger.info("💎 Enriching candidates with project metadata...")
        
        try:
            search_results = state.get("search_results", {})
            candidates = search_results.get("candidates", [])
            
            enriched_candidates = []
            for candidate in candidates:
                enriched_candidate = self._enrich_single_candidate(
                    candidate=candidate,
                    project_id=state["project_id"],
                    naam_project=state["naam_project"],
                    campaign_num=state["campaign_num"],
                    search_metadata=search_results.get("search_metadata", {})
                )
                enriched_candidates.append(enriched_candidate)
            
            state["enriched_candidates"] = enriched_candidates
            state["current_step"] = "candidates_enriched"
            
            logger.info(f"✅ Enriched {len(enriched_candidates)} candidates")
            return state
            
        except Exception as e:
            error_msg = f"Candidate enrichment failed: {e}"
            logger.error(f"❌ {error_msg}")
            state["success"] = False
            state["error_message"] = error_msg
            return state
    
    def _match_candidates_optional(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Optionally match candidates against job requirements."""
        job_requirements = state.get("job_requirements")
        
        if not job_requirements:
            logger.info("⏭️ No job requirements provided, skipping matching")
            state["current_step"] = "matching_skipped"
            return state
        
        logger.info("🎯 Matching candidates against job requirements...")
        
        try:
            # Prepare candidates data for matching
            candidates_data = {
                "candidates": state["enriched_candidates"]
            }
            candidates_json = json.dumps(candidates_data)
            
            # Call matching tool
            matched_result_json = match_candidates_to_job.invoke({
                "candidates_json": candidates_json,
                "job_description": job_requirements
            })
            
            matched_results = json.loads(matched_result_json)
            
            state["matched_candidates"] = matched_results
            state["current_step"] = "candidates_matched"
            
            logger.info(f"✅ Matched {len(matched_results)} candidates")
            return state
            
        except Exception as e:
            error_msg = f"Candidate matching failed: {e}"
            logger.error(f"❌ {error_msg}")
            # Don't fail the entire process for matching errors
            state["matched_candidates"] = []
            state["current_step"] = "matching_failed"
            return state
    
    def _prepare_database_payload(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data payload for Database Agent."""
        logger.info("🗃️ Preparing Database Agent payload...")
        
        try:
            database_payload = {
                "projectid": state["project_id"],
                "naam_project": state["naam_project"],
                "campaign_num": state["campaign_num"],
                "candidates": state["enriched_candidates"],
                "search_metadata": state.get("search_results", {}).get("search_metadata", {}),
                "processing_timestamp": datetime.now().isoformat(),
                "total_candidates": len(state["enriched_candidates"])
            }
            
            # Add matching results if available
            if state.get("matched_candidates"):
                database_payload["candidate_matching"] = state["matched_candidates"]
            
            state["database_payload"] = database_payload
            state["current_step"] = "database_payload_ready"
            
            logger.info(f"✅ Database payload prepared: {len(state['enriched_candidates'])} candidates")
            return state
            
        except Exception as e:
            error_msg = f"Database payload preparation failed: {e}"
            logger.error(f"❌ {error_msg}")
            state["success"] = False
            state["error_message"] = error_msg
            return state
    
    def _prepare_sourcing_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare summary for Sourcing Manager."""
        logger.info("📊 Preparing Sourcing Manager summary...")
        
        try:
            enriched_candidates = state["enriched_candidates"]
            search_metadata = state.get("search_results", {}).get("search_metadata", {})
            
            # Prepare top candidates (first 5)
            top_candidates = enriched_candidates[:5] if enriched_candidates else []
            
            # Calculate summary statistics
            otw_candidates = [c for c in enriched_candidates if c.get("otw") == "Yes"]
            
            sourcing_summary = {
                "projectid": state["project_id"],
                "naam_project": state["naam_project"], 
                "campaign_num": state["campaign_num"],
                "search_id": state["search_id"],
                "total_candidates_found": len(enriched_candidates),
                "open_to_work_candidates": len(otw_candidates),
                "search_timestamp": search_metadata.get("search_timestamp", ""),
                "search_criteria_used": search_metadata.get("search_criteria", {}),
                "top_candidates": top_candidates,
                "matching_completed": bool(state.get("matched_candidates")),
                "processing_status": "completed"
            }
            
            # Add matching insights if available
            if state.get("matched_candidates"):
                matched_results = state["matched_candidates"]
                if matched_results:
                    top_match = matched_results[0]
                    sourcing_summary["top_match_score"] = top_match.get("match_analysis", {}).get("overall_score", 0)
                    sourcing_summary["matching_summary"] = f"{len([m for m in matched_results if m.get('match_analysis', {}).get('overall_score', 0) >= 70])} high-quality matches found"
            
            state["sourcing_manager_summary"] = sourcing_summary
            state["current_step"] = "sourcing_summary_ready"
            
            logger.info(f"✅ Sourcing Manager summary prepared")
            return state
            
        except Exception as e:
            error_msg = f"Sourcing summary preparation failed: {e}"
            logger.error(f"❌ {error_msg}")
            state["success"] = False
            state["error_message"] = error_msg
            return state
    
    def _finalize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the response and mark as successful."""
        logger.info("✅ Finalizing Candidate Searching Agent response...")
        
        if not state.get("error_message"):
            state["success"] = True
            state["current_step"] = "completed"
            
            total_candidates = len(state.get("enriched_candidates", []))
            logger.info(f"🎉 {self.name} completed successfully: {total_candidates} candidates processed")
        else:
            logger.error(f"❌ {self.name} completed with errors: {state['error_message']}")
        
        return state
    
    def _enrich_single_candidate(
        self,
        candidate: Dict[str, Any],
        project_id: str,
        naam_project: str,
        campaign_num: str,
        search_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich a single candidate with project metadata."""
        
        return {
            # Project metadata (required by Database Agent)
            "projectid": project_id,
            "naam_project": naam_project,
            "campaign_num": campaign_num,
            
            # Core candidate data (required by specification)  
            "provider_id": candidate.get("provider_id", ""),
            "naam": candidate.get("naam", ""),
            "positie": candidate.get("positie", ""),
            "headline": candidate.get("headline", ""),
            "locatie": candidate.get("locatie", ""),
            "experience": candidate.get("experience", ""),
            "skills": candidate.get("skills", []),
            "LinkedIn_Beschrijving": candidate.get("LinkedIn_Beschrijving", ""),
            "otw": candidate.get("otw", "Unknown"),
            
            # Additional enriched data
            "profile_url": candidate.get("profile_url", ""),
            "current_company": candidate.get("current_company", ""),
            "previous_companies": candidate.get("previous_companies", []),
            "education": candidate.get("education", []),
            "years_active": candidate.get("years_active", 0),
            "recent_posts": candidate.get("recent_posts", []),
            
            # Metadata
            "found_timestamp": search_metadata.get("search_timestamp", ""),
            "search_criteria_used": search_metadata.get("search_criteria", {}),
            "processed_by": self.name
        }
    
    def _format_skills_for_tool(self, skills: Any) -> str:
        """Format skills parameter for the search tool."""
        if isinstance(skills, list):
            return ",".join(str(skill) for skill in skills)
        elif isinstance(skills, str):
            return skills
        else:
            return ""
    
    def delegate_to_database_agent(self, database_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate candidate storage to Database Agent.
        
        Args:
            database_payload: Prepared candidate data for storage
            
        Returns:
            Result from Database Agent
        """
        logger.info(f"📤 Delegating {len(database_payload.get('candidates', []))} candidates to Database Agent...")
        
        try:
            # For now, simulate database storage since DatabaseAgent needs state parameter
            # In actual implementation, this would create proper DatabaseAgent state and delegate
            
            candidates = database_payload.get('candidates', [])
            
            # Simulate successful storage
            result = {
                "success": True,
                "stored_candidates": len(candidates),
                "storage_timestamp": datetime.now().isoformat(),
                "message": f"Successfully stored {len(candidates)} candidates for project {database_payload.get('projectid')}"
            }
            
            logger.info(f"✅ Database Agent delegation completed (simulated)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Database Agent delegation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stored_candidates": 0
            }

# Factory function for easy instantiation
def create_candidate_searching_agent() -> CandidateSearchingAgent:
    """Create a new Candidate Searching Agent instance."""
    return CandidateSearchingAgent()

