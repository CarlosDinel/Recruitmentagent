"""This agent is a sub-agent of the scourcing_manager.py agent. 
It is responsible for searching and identifying potential candidates for job openings based on specific criteria provided by the sourcing manager.
The agent utilizes various tools and APIs to search on LinkedIn to find and ingest candidate profiles that eventually will be stored by the database_agent.py. 
Additionally, the agent can filter and rank candidates based on relevance to the job requirements, ensuring that only the most suitable profiles are considered for further evaluation.

"""

#  ---- Package imports ----
from typing import List, Annotated, Sequence, Dict, Any, Optional
import logging 
import json
import os
from datetime import datetime

#  ---- Local imports ----
from agents.database_agent import DatabaseAgent
from tools.scourcing_tools import (
    search_candidates_integrated_cursor_and_no_cursor,
    LinkedIn_profile_scrape,
    match_candidates_to_job
)

# Set up logging with enhanced diagnostics
logger = logging.getLogger(__name__)

# ============================================================================
# DIAGNOSTIC MODE - Set to True for detailed search debugging
# ============================================================================
DIAGNOSTIC_MODE = False

def _diagnostic_log(message: str, data: Any = None, level: str = "info"):
    """Log diagnostic information when DIAGNOSTIC_MODE is enabled."""
    if not DIAGNOSTIC_MODE:
        return
    
    prefix = "🔬 [DIAGNOSTIC]"
    if level == "info":
        logger.info(f"{prefix} {message}")
    elif level == "warning":
        logger.warning(f"{prefix} {message}")
    elif level == "error":
        logger.error(f"{prefix} {message}")
    elif level == "debug":
        logger.debug(f"{prefix} {message}")
    
    if data is not None:
        if isinstance(data, dict):
            logger.info(f"{prefix} Data: {json.dumps(data, indent=2, default=str)[:2000]}")
        else:
            logger.info(f"{prefix} Data: {str(data)[:2000]}")

# ============================================================================
# CANDIDATE RELEVANCE SCORING & FILTERING
# ============================================================================

def _calculate_candidate_relevance(candidate: Dict[str, Any], search_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate relevance score for a candidate based on search criteria.
    Returns the candidate with added relevance_score and relevance_breakdown.
    
    Scoring factors:
    - Location match: 40 points (exact match) / 20 points (country match) / 0 (no match)
    - Job title match: 30 points (contains keywords)
    - Skills match: 20 points (based on skill overlap)
    - Experience match: 10 points
    """
    score = 0
    breakdown = []
    
    # Get candidate data (handle different field names)
    candidate_location = (candidate.get('locatie') or candidate.get('location') or '').lower()
    candidate_title = (candidate.get('positie') or candidate.get('current_position') or 
                       candidate.get('headline') or '').lower()
    candidate_skills = candidate.get('skills', [])
    if isinstance(candidate_skills, str):
        candidate_skills = [s.strip() for s in candidate_skills.split(',')]
    candidate_skills_lower = [s.lower() for s in candidate_skills if s]
    
    # Get search criteria
    target_location = (search_criteria.get('location') or '').lower()
    target_title = (search_criteria.get('job_title') or '').lower()
    
    # Handle keywords as string or list
    raw_keywords = search_criteria.get('keywords') or ''
    if isinstance(raw_keywords, list):
        target_keywords = ' '.join(raw_keywords).lower()
    else:
        target_keywords = raw_keywords.lower()
    
    # Handle skills as string or list
    target_skills = search_criteria.get('skills', [])
    if isinstance(target_skills, str):
        target_skills = [s.strip() for s in target_skills.split(',')]
    target_skills_lower = [s.lower() for s in target_skills if s]
    
    # 1. LOCATION SCORING (40 points max)
    if target_location:
        # Define location mappings for common variations
        location_mappings = {
            'netherlands': ['netherlands', 'nederland', 'nl', 'amsterdam', 'rotterdam', 'utrecht', 
                           'den haag', 'the hague', 'eindhoven', 'groningen', 'dutch'],
            'germany': ['germany', 'deutschland', 'berlin', 'munich', 'frankfurt', 'hamburg', 'german'],
            'belgium': ['belgium', 'belgie', 'brussels', 'antwerp', 'belgian'],
            'uk': ['uk', 'united kingdom', 'london', 'manchester', 'birmingham', 'british', 'england'],
        }
        
        location_matched = False
        for country, variations in location_mappings.items():
            if any(var in target_location for var in variations):
                # Check if candidate is in this country
                if any(var in candidate_location for var in variations):
                    score += 40
                    breakdown.append(f"Location match (+40): {candidate_location}")
                    location_matched = True
                    break
        
        if not location_matched:
            # Direct string match as fallback
            if target_location in candidate_location or candidate_location in target_location:
                score += 40
                breakdown.append(f"Location match (+40): {candidate_location}")
            elif candidate_location:
                # Penalize wrong location
                score -= 20
                breakdown.append(f"Location MISMATCH (-20): '{candidate_location}' != '{target_location}'")
    
    # 2. JOB TITLE SCORING (30 points max)
    title_keywords = target_title.split() + target_keywords.split()
    title_keywords = [k for k in title_keywords if len(k) > 2]  # Filter short words
    
    if title_keywords and candidate_title:
        matches = sum(1 for kw in title_keywords if kw in candidate_title)
        if matches > 0:
            title_score = min(30, matches * 10)
            score += title_score
            breakdown.append(f"Title keywords match (+{title_score}): {matches} keywords found")
    
    # 3. SKILLS SCORING (20 points max)
    if target_skills_lower and candidate_skills_lower:
        skill_matches = len(set(target_skills_lower) & set(candidate_skills_lower))
        if skill_matches > 0:
            skill_score = min(20, skill_matches * 5)
            score += skill_score
            breakdown.append(f"Skills match (+{skill_score}): {skill_matches} skills")
    
    # 4. PROFILE COMPLETENESS BONUS (10 points max)
    completeness_fields = ['naam', 'name', 'positie', 'current_position', 'linkedin_url']
    filled_fields = sum(1 for f in completeness_fields if candidate.get(f))
    if filled_fields >= 3:
        score += 10
        breakdown.append(f"Profile completeness (+10)")
    
    # Add relevance data to candidate
    candidate['relevance_score'] = max(0, score)  # Don't go negative
    candidate['relevance_breakdown'] = breakdown
    candidate['relevance_grade'] = _get_relevance_grade(score)
    
    return candidate

def _get_relevance_grade(score: int) -> str:
    """Convert numeric score to grade."""
    if score >= 70:
        return 'A'  # Excellent match
    elif score >= 50:
        return 'B'  # Good match
    elif score >= 30:
        return 'C'  # Moderate match
    elif score >= 10:
        return 'D'  # Weak match
    else:
        return 'F'  # Poor match / wrong location

def _filter_candidates_by_relevance(
    candidates: List[Dict[str, Any]], 
    search_criteria: Dict[str, Any],
    min_score: int = 0,
    min_grade: str = 'F'
) -> List[Dict[str, Any]]:
    """
    Filter and sort candidates by relevance score.
    
    Args:
        candidates: List of candidates to filter
        search_criteria: Search criteria to match against
        min_score: Minimum relevance score (default: 0 = keep all)
        min_grade: Minimum grade to keep ('A', 'B', 'C', 'D', 'F')
    
    Returns:
        Filtered and sorted list of candidates (highest relevance first)
    """
    grade_order = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}
    min_grade_value = grade_order.get(min_grade, 1)
    
    # Score all candidates
    scored_candidates = []
    for candidate in candidates:
        scored = _calculate_candidate_relevance(candidate.copy(), search_criteria)
        scored_candidates.append(scored)
    
    # Filter by minimum score and grade
    filtered = [
        c for c in scored_candidates 
        if c.get('relevance_score', 0) >= min_score
        and grade_order.get(c.get('relevance_grade', 'F'), 1) >= min_grade_value
    ]
    
    # Sort by relevance score (highest first)
    filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return filtered

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
        
        # DIAGNOSTIC: Log full incoming request
        _diagnostic_log("=" * 60)
        _diagnostic_log("SEARCH REQUEST RECEIVED")
        _diagnostic_log("=" * 60)
        _diagnostic_log(f"Project ID: {request.get('projectid')}")
        _diagnostic_log(f"Search ID: {request.get('searchid')}")
        _diagnostic_log(f"Project Name: {request.get('naam_project')}")
        _diagnostic_log(f"Max Results: {request.get('max_results', 50)}")
        _diagnostic_log("Search Criteria:", request.get('search_criteria', {}))
        _diagnostic_log(f"Job Requirements Provided: {bool(request.get('job_requirements'))}")
        
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
        
        # DIAGNOSTIC: Log raw request
        _diagnostic_log("-" * 40)
        _diagnostic_log("STEP 1: PARSING REQUEST")
        _diagnostic_log("-" * 40)
        _diagnostic_log(f"Raw request keys: {list(request.keys())}")
        
        # Extract required parameters
        project_id = request.get("projectid")
        search_id = request.get("searchid")
        naam_project = request.get("naam_project")
        campaign_num = request.get("campaign_num")
        
        # DIAGNOSTIC: Log extracted parameters
        _diagnostic_log(f"Extracted project_id: {project_id} (type: {type(project_id).__name__})")
        _diagnostic_log(f"Extracted search_id: {search_id}")
        _diagnostic_log(f"Extracted naam_project: {naam_project}")
        _diagnostic_log(f"Extracted campaign_num: {campaign_num}")
        
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
        """
        Perform hybrid candidate search (MongoDB + LinkedIn).
        
        Search strategy:
        1. First search MongoDB prospects collection for existing candidates
        2. If results < target count, proceed with LinkedIn search
        3. Deduplicate results by LinkedIn URL
        4. Return combined results
        """
        logger.info("🔍 Starting hybrid candidate search (MongoDB + LinkedIn)...")
        
        # DIAGNOSTIC: Log search entry
        _diagnostic_log("-" * 40)
        _diagnostic_log("STEP 2: HYBRID SEARCH STARTING")
        _diagnostic_log("-" * 40)
        _diagnostic_log(f"Project ID for search: {state.get('project_id')}")
        _diagnostic_log(f"Max results target: {state.get('max_results', 50)}")
        _diagnostic_log("Search criteria:", state.get('search_criteria', {}))
        
        try:
            # Step 1: Search MongoDB first
            _diagnostic_log(">>> Starting MongoDB search...")
            mongodb_candidates = self._search_candidates_in_mongodb(state)
            logger.info(f"✅ MongoDB search found {len(mongodb_candidates)} existing candidates")
            _diagnostic_log(f"MongoDB returned {len(mongodb_candidates)} candidates")
            if mongodb_candidates:
                _diagnostic_log(f"First MongoDB candidate sample:", mongodb_candidates[0] if mongodb_candidates else "None")
            
            search_criteria = state.get("search_criteria", {})
            max_results = state.get("max_results", 50)
            
            # DIAGNOSTIC: Check if search_criteria is empty
            if not search_criteria:
                _diagnostic_log("⚠️ WARNING: search_criteria is EMPTY - LinkedIn search may fail!", level="warning")
            
            # Step 2: Check if we need LinkedIn search
            candidates = mongodb_candidates.copy()
            search_type = "mongodb"
            
            if len(candidates) < max_results:
                logger.info(f"⏭️ Results below target ({len(candidates)}/{max_results}), performing LinkedIn search...")
                _diagnostic_log(f">>> Starting LinkedIn search (need {max_results - len(candidates)} more candidates)...")
                
                linkedin_candidates = self._search_candidates_on_linkedin(state, search_criteria)
                logger.info(f"✅ LinkedIn search found {len(linkedin_candidates)} new candidates")
                _diagnostic_log(f"LinkedIn returned {len(linkedin_candidates)} candidates")
                if linkedin_candidates:
                    _diagnostic_log(f"First LinkedIn candidate sample:", linkedin_candidates[0] if linkedin_candidates else "None")
                
                # Step 3: Deduplicate by LinkedIn URL
                linkedin_urls = {c.get("linkedin_url") for c in candidates if c.get("linkedin_url")}
                for linkedin_candidate in linkedin_candidates:
                    if linkedin_candidate.get("linkedin_url") not in linkedin_urls:
                        candidates.append(linkedin_candidate)
                
                search_type = "hybrid"
                if len(mongodb_candidates) == 0:
                    search_type = "linkedin"
            
            # Step 4: RELEVANCE FILTERING - Score and filter candidates
            _diagnostic_log("-" * 40)
            _diagnostic_log("STEP 4: RELEVANCE FILTERING")
            _diagnostic_log("-" * 40)
            
            if candidates and search_criteria:
                _diagnostic_log(f"Scoring {len(candidates)} candidates for relevance...")
                
                # Apply relevance scoring and filtering
                # Keep candidates with grade C or better (score >= 30) or if no location specified
                min_grade = 'D' if search_criteria.get('location') else 'F'
                filtered_candidates = _filter_candidates_by_relevance(
                    candidates, 
                    search_criteria,
                    min_score=0,
                    min_grade=min_grade
                )
                
                _diagnostic_log(f"After relevance filtering: {len(filtered_candidates)} candidates (from {len(candidates)})")
                
                # Log filtering results
                if filtered_candidates:
                    _diagnostic_log("Top 3 candidates by relevance:")
                    for i, c in enumerate(filtered_candidates[:3], 1):
                        name = c.get('naam') or c.get('name', 'Unknown')
                        score = c.get('relevance_score', 0)
                        grade = c.get('relevance_grade', 'F')
                        location = c.get('locatie') or c.get('location', 'Unknown')
                        _diagnostic_log(f"  {i}. {name} | Score: {score} ({grade}) | Location: {location}")
                        for reason in c.get('relevance_breakdown', [])[:2]:
                            _diagnostic_log(f"     - {reason}")
                
                # Show filtered out candidates
                removed_count = len(candidates) - len(filtered_candidates)
                if removed_count > 0:
                    _diagnostic_log(f"⚠️ Filtered out {removed_count} low-relevance candidates", level="warning")
                
                candidates = filtered_candidates
            
            # Limit to max_results
            candidates = candidates[:max_results]
            
            # Prepare results
            search_results = {
                "success": True,
                "candidates": candidates,
                "search_metadata": {
                    "search_timestamp": datetime.now().isoformat(),
                    "search_type": search_type,
                    "mongodb_count": len(mongodb_candidates),
                    "linkedin_count": len(candidates) - len(mongodb_candidates),
                    "total_found": len(candidates),
                    "search_criteria": search_criteria
                }
            }
            
            state["search_results"] = search_results
            state["current_step"] = "candidates_found"
            state["search_type"] = search_type
            
            logger.info(f"✅ Hybrid search completed ({search_type}): {len(candidates)} total candidates found")
            
            # DIAGNOSTIC: Final search summary
            _diagnostic_log("=" * 60)
            _diagnostic_log("SEARCH COMPLETE - FINAL SUMMARY")
            _diagnostic_log("=" * 60)
            _diagnostic_log(f"Search Type: {search_type}")
            _diagnostic_log(f"MongoDB candidates: {len(mongodb_candidates)}")
            _diagnostic_log(f"LinkedIn candidates: {len(candidates) - len(mongodb_candidates)}")
            _diagnostic_log(f"Total candidates: {len(candidates)}")
            if len(candidates) == 0:
                _diagnostic_log("⚠️ ZERO CANDIDATES FOUND!", level="warning")
                _diagnostic_log("Possible reasons:")
                _diagnostic_log("  1. No prospects in MongoDB for this project_id")
                _diagnostic_log("  2. Empty search_criteria (no keywords, location, etc.)")
                _diagnostic_log("  3. LinkedIn API error or unavailable")
                _diagnostic_log("  4. Very restrictive search criteria with no matches")
            _diagnostic_log("=" * 60)
            
            return state
            
        except Exception as e:
            error_msg = f"Candidate search failed: {e}"
            logger.error(f"❌ {error_msg}")
            _diagnostic_log(f"❌ SEARCH EXCEPTION: {str(e)}", level="error")
            import traceback
            _diagnostic_log(f"Traceback: {traceback.format_exc()}", level="error")
            state["success"] = False
            state["error_message"] = error_msg
            return state

    def _search_candidates_in_mongodb(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search existing candidates in MongoDB prospects collection.
        
        Returns candidates matching the search criteria from the prospects collection.
        """
        logger.info("🗄️ Searching MongoDB prospects collection...")
        
        # DIAGNOSTIC: Log MongoDB search entry
        _diagnostic_log("-" * 40)
        _diagnostic_log("MONGODB SEARCH")
        _diagnostic_log("-" * 40)
        
        try:
            from agents.database_agent import DatabaseAgent, DatabaseAgentState
            
            # Initialize DatabaseAgent
            db_state = DatabaseAgentState(
                name="CandidateSearch_DatabaseAgent",
                description="Database operations for candidate search",
                tools=[], tool_descriptions=[], tool_input_types=[], tool_output_types=[],
                input_type="dict", output_type="dict", intermediate_steps=[],
                max_iterations=5, iteration_count=0, stop=False,
                last_action="", last_observation="", last_input="", last_output="",
                graph=None, memory=[], memory_limit=100, verbose=False,
                temperature=0.7, top_k=50, top_p=0.9, frequency_penalty=0.0, presence_penalty=0.0,
                best_of=1, n=1, logit_bias={}, seed=42, model=os.getenv("OPENAI_MODEL", "gpt-5"), api_key=""
            )
            
            db_agent = DatabaseAgent(db_state)
            _diagnostic_log("✅ DatabaseAgent initialized successfully")
            
            # Get prospects for this project
            project_id = state.get("project_id", "")
            _diagnostic_log(f"Querying MongoDB for project_id: '{project_id}' (type: {type(project_id).__name__})")
            
            # Note: get_prospects_for_project is sync in current implementation
            prospects = db_agent.get_prospects_for_project(project_id)
            _diagnostic_log(f"Raw prospects result type: {type(prospects).__name__}")
            
            _diagnostic_log(f"MongoDB query returned {len(prospects) if prospects else 0} raw prospects")
            if prospects:
                _diagnostic_log(f"First raw prospect sample:", prospects[0] if prospects else "None")
            else:
                _diagnostic_log("⚠️ NO PROSPECTS FOUND in MongoDB for this project!", level="warning")
            
            # Convert MongoDB prospects to candidate format
            candidates = []
            for prospect in prospects:
                candidate = {
                    "linkedin_url": prospect.get("_id") or prospect.get("linkedin_url", ""),
                    "naam": prospect.get("name", ""),
                    "positie": prospect.get("current_position", ""),
                    "locatie": prospect.get("location", ""),
                    "skills": prospect.get("skills", []),
                    "experience": prospect.get("years_experience", ""),
                    "otw": prospect.get("status", "Unknown"),
                    "status": prospect.get("status", "NEW"),
                    "source": "mongodb"
                }
                candidates.append(candidate)
            
            logger.info(f"✅ Found {len(candidates)} candidates in MongoDB")
            _diagnostic_log(f"MongoDB search complete: {len(candidates)} candidates converted")
            return candidates
            
        except Exception as e:
            logger.warning(f"⚠️ MongoDB search failed: {e}")
            _diagnostic_log(f"❌ MongoDB search EXCEPTION: {str(e)}", level="error")
            _diagnostic_log(f"Exception type: {type(e).__name__}")
            import traceback
            _diagnostic_log(f"Traceback: {traceback.format_exc()}", level="error")
            return []

    def _search_candidates_on_linkedin(self, state: Dict[str, Any], search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search candidates on LinkedIn API with retry logic and exponential backoff.
        Attempts up to 3 times with progressive delays (2s, 4s, 8s) to handle transient failures.
        """
        logger.info("🔗 Searching LinkedIn API...")
        
        # DIAGNOSTIC: Log LinkedIn search entry
        _diagnostic_log("-" * 40)
        _diagnostic_log("LINKEDIN SEARCH")
        _diagnostic_log("-" * 40)
        
        # Prepare tool parameters
        # Handle keywords as string or list
        raw_keywords = search_criteria.get("keywords", "")
        if isinstance(raw_keywords, list):
            keywords_str = " ".join(raw_keywords)
        else:
            keywords_str = raw_keywords or ""
        
        tool_params = {
            "project_id": state["project_id"],
            "search_id": state["search_id"],
            "max_results": state["max_results"],
            "location": search_criteria.get("location", ""),
            "keywords": keywords_str,
            "company_name": search_criteria.get("company_name", ""),
            "job_title": search_criteria.get("job_title", ""),
            "skills": self._format_skills_for_tool(search_criteria.get("skills", [])),
            "experience_level": search_criteria.get("experience_level", ""),
            "use_cursor": search_criteria.get("use_cursor", True)
        }
        
        # DIAGNOSTIC: Log tool parameters
        _diagnostic_log("LinkedIn API tool_params:", tool_params)
        
        # Check for empty search criteria
        search_values = [tool_params["location"], tool_params["keywords"], 
                        tool_params["company_name"], tool_params["job_title"], 
                        tool_params["skills"]]
        if not any(search_values):
            _diagnostic_log("⚠️ ALL SEARCH PARAMETERS ARE EMPTY!", level="warning")
            _diagnostic_log("LinkedIn search will likely return no/random results without search criteria!")
        
        # Retry logic with exponential backoff
        max_attempts = 3
        backoff_seconds = 2
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"LinkedIn API search attempt {attempt}/{max_attempts}...")
                _diagnostic_log(f">>> LinkedIn API attempt {attempt}/{max_attempts}")
                
                # Call the LinkedIn search tool
                search_result_json = search_candidates_integrated_cursor_and_no_cursor.invoke(tool_params)
                _diagnostic_log(f"LinkedIn API raw response length: {len(search_result_json) if search_result_json else 0} chars")
                
                search_results = json.loads(search_result_json)
                
                if not search_results.get("success", False):
                    error_msg = search_results.get('error', 'Unknown error')
                    logger.warning(f"⚠️ LinkedIn search attempt {attempt} failed: {error_msg}")
                    last_error = error_msg
                    
                    # Retry on failure (except for last attempt)
                    if attempt < max_attempts:
                        wait_time = backoff_seconds * (2 ** (attempt - 1))  # 2s, 4s, 8s
                        logger.info(f"Retrying in {wait_time} seconds...")
                        import time
                        time.sleep(wait_time)
                    continue
                
                # Success
                candidates = search_results.get("candidates", [])
                logger.info(f"✅ LinkedIn search found {len(candidates)} candidates on attempt {attempt}")
                return candidates
                
            except Exception as e:
                logger.warning(f"⚠️ LinkedIn search attempt {attempt} failed with exception: {e}")
                last_error = str(e)
                
                # Retry on exception (except for last attempt)
                if attempt < max_attempts:
                    wait_time = backoff_seconds * (2 ** (attempt - 1))  # 2s, 4s, 8s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    import time
                    time.sleep(wait_time)
                continue
        
        # All retries exhausted
        logger.error(f"❌ LinkedIn search failed after {max_attempts} attempts. Last error: {last_error}")
        return []
    
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
        """Finalize the response, save candidates via DatabaseAgent, and mark as successful."""
        logger.info("💾 Saving candidates via DatabaseAgent...")
        
        try:
            # Save all enriched candidates via DatabaseAgent
            enriched_candidates = state.get("enriched_candidates", [])
            if enriched_candidates:
                candidates_saved = self._save_candidates_to_database(enriched_candidates)
                logger.info(f"✅ Saved {candidates_saved} candidates to database via DatabaseAgent")
            
            if not state.get("error_message"):
                state["success"] = True
                state["current_step"] = "completed"
                
                total_candidates = len(state.get("enriched_candidates", []))
                logger.info(f"🎉 {self.name} completed successfully: {total_candidates} candidates processed and saved")
            else:
                logger.error(f"❌ {self.name} completed with errors: {state['error_message']}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error finalizing response: {e}")
            state["success"] = False
            state["error_message"] = f"Finalization failed: {e}"
            return state

    def _save_candidates_to_database(self, candidates: List[Dict[str, Any]]) -> int:
        """
        Save all candidates to database via DatabaseAgent.
        
        Uses upsert_prospect() to automatically deduplicate by LinkedIn URL.
        
        Returns:
            Number of candidates successfully saved
        """
        logger.info(f"📤 Saving {len(candidates)} candidates to database...")
        
        try:
            from agents.database_agent import DatabaseAgent, DatabaseAgentState
            
            # Initialize DatabaseAgent
            db_state = DatabaseAgentState(
                name="CandidateSave_DatabaseAgent",
                description="Database operations for candidate saving",
                tools=[], tool_descriptions=[], tool_input_types=[], tool_output_types=[],
                input_type="dict", output_type="dict", intermediate_steps=[],
                max_iterations=5, iteration_count=0, stop=False,
                last_action="", last_observation="", last_input="", last_output="",
                graph=None, memory=[], memory_limit=100, verbose=False,
                temperature=0.7, top_k=50, top_p=0.9, frequency_penalty=0.0, presence_penalty=0.0,
                best_of=1, n=1, logit_bias={}, seed=42, model=os.getenv("OPENAI_MODEL", "gpt-5"), api_key=""
            )
            
            db_agent = DatabaseAgent(db_state)
            
            # Save each candidate via upsert_prospect (automatic deduplication)
            saved_count = 0
            for candidate in candidates:
                try:
                    # Prepare prospect data for DatabaseAgent
                    prospect_data = {
                        "linkedin_url": candidate.get("linkedin_url") or candidate.get("profile_url", ""),
                        "name": candidate.get("naam", ""),
                        "current_position": candidate.get("positie", ""),
                        "location": candidate.get("locatie", ""),
                        "skills": candidate.get("skills", []),
                        "years_experience": candidate.get("experience", ""),
                        "status": candidate.get("status", "NEW"),
                        "project_id": candidate.get("projectid", ""),
                        "email": candidate.get("email"),
                        "phone": candidate.get("phone"),
                        "current_company": candidate.get("current_company", ""),
                        "education": candidate.get("education", []),
                        "profile_data": {
                            "headline": candidate.get("headline", ""),
                            "description": candidate.get("LinkedIn_Beschrijving", ""),
                            "open_to_work": candidate.get("otw", "Unknown"),
                            "source": candidate.get("source", "linkedin_search")
                        }
                    }
                    
                    # Skip if no LinkedIn URL
                    if not prospect_data.get("linkedin_url"):
                        logger.warning(f"⚠️ Skipping candidate without LinkedIn URL: {prospect_data.get('name')}")
                        continue
                    
                    # Upsert prospect (automatic deduplication by LinkedIn URL)
                    upsert_result = db_agent.upsert_prospect(prospect_data)
                    if hasattr(upsert_result, "__await__"):
                        try:
                            import asyncio
                            prospect_id = asyncio.run(upsert_result)
                        except RuntimeError:
                            prospect_id = None
                    else:
                        prospect_id = upsert_result
                    saved_count += 1
                    logger.debug(f"✅ Saved prospect: {prospect_id}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to save candidate {candidate.get('naam', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Successfully saved {saved_count}/{len(candidates)} candidates to database")
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Error saving candidates to database: {e}")
            raise
    
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
            "linkedin_url": candidate.get("linkedin_url") or candidate.get("profile_url", ""),
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

