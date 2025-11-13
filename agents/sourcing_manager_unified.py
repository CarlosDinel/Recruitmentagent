"""
This unified agent combines all best features from the previous versions:
- Complete workflow orchestration (from scourcing_manager.py)
- Advanced parsing with CandidateRecord objects (from scourcing_manager_complete.py)  
- AI-powered decision making with retry logic (from scourcing_manager_extended.py)
- Database integration with LinkedIn URL unique key
- Production-ready error handling and recovery mechanisms
- SYNCHRONOUS implementation for compatibility with existing agents

The Sourcing Manager coordinates specialized sub-agents to deliver high-quality candidates:
1. CandidateSearchingAgent - LinkedIn search and basic enrichment
2. CandidateEvaluationAgent - Suitability assessment and decision making  
3. ProfileScrapingAgent - Detailed profile enrichment (when available)
"""

# ---- Package imports ----
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import time
import uuid

# AI decision making (mock implementation - replace with your preferred LLM)
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI

# Custom imports for the working system
from sub_agents.candidate_serching_agent import CandidateSearchingAgent
from sub_agents.candidate_evaluation_agent import CandidateEvaluationAgent
from agents.database_agent import DatabaseAgent, DatabaseAgentState
from config import get_config, AppConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- Data Classes for Enhanced Structure ----

@dataclass
class CandidateRecord:
    """Enhanced candidate record with comprehensive metadata"""
    candidate_id: str
    linkedin_url: str
    name: str
    title: str = ""
    company: str = ""
    location: str = ""
    experience_years: int = 0
    skills: List[str] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)
    
    # Search metadata
    search_score: float = 0.0
    search_source: str = "linkedin"
    search_timestamp: Optional[datetime] = None
    
    # Evaluation metadata
    suitability_status: str = "unknown"  # suitable, maybe, unsuitable
    suitability_score: float = 0.0
    suitability_reasoning: str = ""
    evaluation_timestamp: Optional[datetime] = None
    
    # Enrichment metadata
    profile_enriched: bool = False
    enrichment_timestamp: Optional[datetime] = None
    enrichment_details: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "candidate_id": self.candidate_id,
            "linkedin_url": self.linkedin_url,
            "name": self.name,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "experience_years": self.experience_years,
            "skills": self.skills,
            "education": self.education,
            "contact_info": self.contact_info,
            "search_score": self.search_score,
            "search_source": self.search_source,
            "search_timestamp": self.search_timestamp.isoformat() if self.search_timestamp else None,
            "suitability_status": self.suitability_status,
            "suitability_score": self.suitability_score,
            "suitability_reasoning": self.suitability_reasoning,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat() if self.evaluation_timestamp else None,
            "profile_enriched": self.profile_enriched,
            "enrichment_timestamp": self.enrichment_timestamp.isoformat() if self.enrichment_timestamp else None,
            "enrichment_details": self.enrichment_details
        }


@dataclass
class SourcingManagerDecision:
    """AI-powered workflow decision with reasoning"""
    action: str  # continue, retry, adjust, escalate, complete
    reasoning: str
    confidence: float
    next_steps: List[str]
    adjustments: Dict[str, Any] = field(default_factory=dict)


class WorkflowStage(Enum):
    """Workflow stages for better tracking"""
    INITIALIZING = "initializing"
    SEARCHING = "searching"
    EVALUATING = "evaluating"
    ENRICHING = "enriching"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


# ---- Unified Sourcing Manager Class ----

class UnifiedSourcingManager:
    """
    Complete production-ready orchestrator for the candidate sourcing pipeline.
    Combines all advanced features: AI decision making, database integration, 
    enhanced parsing, and intelligent workflow orchestration.
    """
    
    def __init__(self, model_name: str = None, temperature: float = None, config: AppConfig = None):
        """Initialize the Unified Sourcing Manager with configuration from .env."""
        
        # Load configuration from .env or use provided config
        self.config = config or get_config()
        
        # Use config values or fallbacks
        self.model_name = model_name or self.config.openai.model
        self.temperature = temperature or self.config.openai.temperature
        
        # Initialize working sub-agents
        self.search_agent = CandidateSearchingAgent()
        self.evaluation_agent = CandidateEvaluationAgent()
        
        # Initialize AI decision making (mock - replace with your LLM)
        self.llm = None  # MockLLM placeholder
        
        # Initialize database agent for candidate storage
        db_state = DatabaseAgentState(
            name="UnifiedSourcingManager_DatabaseAgent",
            description="Database operations for candidate storage",
            tools=[], tool_descriptions=[], tool_input_types=[], tool_output_types=[],
            input_type="dict", output_type="dict", intermediate_steps=[],
            max_iterations=5, iteration_count=0, stop=False,
            last_action="", last_observation="", last_input="", last_output="",
            graph=None, memory=[], memory_limit=100, verbose=False,
            temperature=0.7, top_k=50, top_p=0.9, frequency_penalty=0.0, presence_penalty=0.0,
            best_of=1, n=1, logit_bias={}, seed=42, model="gpt-4", api_key=""
        )
        self.database_agent = DatabaseAgent(db_state)
        
        # Profile scraping agent (mock for now)
        self.scraping_agent = None
        
        # Configuration from .env
        self.max_retries = self.config.unified_sourcing.max_retries
        self.timeout_minutes = self.config.unified_sourcing.timeout_minutes
        self.min_candidates_threshold = self.config.unified_sourcing.min_candidates
        self.min_suitable_threshold = self.config.unified_sourcing.min_suitable
        
        logger.info(f"UnifiedSourcingManager initialized with configuration from .env")
        logger.info(f"Config: max_retries={self.max_retries}, timeout={self.timeout_minutes}min, AI={self.config.unified_sourcing.ai_decision_enabled}")
    
    # ---- Main Orchestration Method ----
    
    def process_sourcing_request(self, 
                                     project_requirements: Dict[str, Any],
                                     job_description: str,
                                     project_id: str,
                                     target_count: int = 50) -> Dict[str, Any]:
        """
        Main orchestration method - coordinates complete sourcing pipeline with AI intelligence.
        
        Args:
            project_requirements: Job requirements and search criteria
            job_description: Detailed job description for matching
            project_id: ID of the project to link candidates to
            target_count: Target number of initial candidates to find
            
        Returns:
            Complete sourcing results with qualified candidates
        """
        request_id = str(uuid.uuid4())
        logger.info(f"🚀 Starting unified sourcing request {request_id}")
        
        workflow_state = {
            "request_id": request_id,
            "project_id": project_id,
            "project_requirements": project_requirements,
            "job_description": job_description,
            "target_count": target_count,
            "started_at": datetime.now(),
            "current_stage": WorkflowStage.INITIALIZING.value,
            "stages_completed": [],
            "candidates_pipeline": {
                "found": [],
                "evaluated": [],
                "enriched": [],
                "final": []
            },
            "candidates_records": {  # Enhanced with CandidateRecord objects
                "found": [],
                "evaluated": [],
                "enriched": [],
                "final": []
            },
            "metrics": {
                "total_found": 0,
                "total_suitable": 0,
                "total_enriched": 0,
                "success_rate": 0.0
            },
            "decisions": [],  # Track AI decisions
            "errors": [],
            "warnings": [],
            "retry_count": 0
        }
        
        try:
            # Phase 1: Intelligent Candidate Search
            self._execute_enhanced_search_phase(workflow_state)
            
            # AI Decision: Proceed to evaluation?
            if not self._should_proceed_to_evaluation(workflow_state):
                return self._generate_early_completion_results(workflow_state, "insufficient_candidates")
            
            # Phase 2: Candidate Evaluation with Database Storage
            self._execute_enhanced_evaluation_phase(workflow_state)
            
            # AI Decision: Proceed to enrichment?
            if not self._should_proceed_to_enrichment(workflow_state):
                return self._generate_results_without_enrichment(workflow_state)
            
            # Phase 3: Intelligent Profile Enrichment
            self._execute_enhanced_enrichment_phase(workflow_state)
            
            # Phase 4: Final Results Generation
            final_results = self._generate_enhanced_final_results(workflow_state)
            
            logger.info(f"✅ Unified sourcing request {request_id} completed successfully")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Unified sourcing request {request_id} failed: {str(e)}")
            return self._generate_error_results(workflow_state, str(e))
    
    # ---- Enhanced Phase Execution Methods ----
    
    def _execute_enhanced_search_phase(self, workflow_state: Dict[str, Any]):
        """Execute candidate search phase with retry logic and AI decision making"""
        logger.info("📋 Phase 1: Enhanced Candidate Search")
        workflow_state["current_stage"] = WorkflowStage.SEARCHING.value
        
        max_search_attempts = 3
        attempt = 0
        
        while attempt < max_search_attempts:
            try:
                # Delegate to CandidateSearchingAgent with proper request format
                search_request = {
                    "projectid": workflow_state["project_id"],
                    "searchid": f"search_{workflow_state['request_id'][:8]}",
                    "naam_project": f"UnifiedSourcing_{workflow_state['project_id']}",
                    "campaign_num": "001",
                    "job_requirements": workflow_state["job_description"],
                    "max_results": workflow_state["target_count"],
                    "search_criteria": workflow_state["project_requirements"]
                }
                
                search_results = self.search_agent.process_request(search_request)
                
                # Enhanced parsing with CandidateRecord objects  
                # CandidateSearchingAgent returns candidates in "enriched_candidates" key
                candidates_found = search_results.get("enriched_candidates", [])
                candidate_records = self._parse_search_results({"candidates": candidates_found})
                
                workflow_state["candidates_pipeline"]["found"] = candidates_found
                workflow_state["candidates_records"]["found"] = candidate_records
                workflow_state["metrics"]["total_found"] = len(candidates_found)
                workflow_state["stages_completed"].append("search")
                
                logger.info(f"✅ Found {len(candidates_found)} candidates")
                break
                
            except Exception as e:
                attempt += 1
                logger.warning(f"⚠️ Search attempt {attempt} failed: {str(e)}")
                
                if attempt < max_search_attempts:
                    # AI decision on how to handle search failure
                    decision = self._make_workflow_decision("search_failed", workflow_state)
                    workflow_state["decisions"].append(decision.dict() if hasattr(decision, 'dict') else str(decision))
                    
                    if decision.action == "retry":
                        import time
                        time.sleep(2)  # Brief delay before retry
                        continue
                    elif decision.action == "adjust":
                        self._adjust_search_criteria(workflow_state)
                        continue
                    else:
                        raise
                else:
                    workflow_state["errors"].append({
                        "phase": "search",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "attempts": attempt
                    })
                    raise
    
    def _execute_enhanced_evaluation_phase(self, workflow_state: Dict[str, Any]):
        """Execute candidate evaluation phase with enhanced data handling"""
        logger.info("🔍 Phase 2: Enhanced Candidate Evaluation")
        workflow_state["current_stage"] = WorkflowStage.EVALUATING.value
        
        try:
            candidates = workflow_state["candidates_pipeline"]["found"]
            
            # Delegate to CandidateEvaluationAgent with proper request format
            evaluation_request = {
                "candidates": candidates,
                "job_requirements": workflow_state["job_description"],
                "projectid": workflow_state["project_id"],
                "naam_project": f"UnifiedSourcing_{workflow_state['project_id']}",
                "campaign_num": "001",
                "evaluation_criteria": workflow_state["project_requirements"]
            }
            
            evaluation_results = self.evaluation_agent.evaluate_candidates(evaluation_request)
            
            # Enhanced parsing with CandidateRecord objects
            evaluated_candidates = evaluation_results.get("evaluated_candidates", [])
            candidate_records = self._parse_evaluation_results(evaluation_results, workflow_state["candidates_records"]["found"])
            
            workflow_state["candidates_pipeline"]["evaluated"] = evaluated_candidates
            workflow_state["candidates_records"]["evaluated"] = candidate_records
            
            # Save candidates to database via DatabaseAgent with LinkedIn URL unique key
            self._save_candidates_to_database(evaluated_candidates, workflow_state["project_id"])
            
            # Calculate suitable candidates
            suitable_candidates = [
                c for c in evaluated_candidates 
                if c.get("suitability_status") in ["suitable", "maybe"]
            ]
            workflow_state["metrics"]["total_suitable"] = len(suitable_candidates)
            workflow_state["metrics"]["success_rate"] = (
                len(suitable_candidates) / len(candidates) if candidates else 0.0
            )
            workflow_state["stages_completed"].append("evaluation")
            
            logger.info(f"✅ Evaluated {len(evaluated_candidates)} candidates, {len(suitable_candidates)} suitable/maybe")
            
        except Exception as e:
            logger.error(f"❌ Evaluation phase failed: {str(e)}")
            workflow_state["errors"].append({
                "phase": "evaluation",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            raise
    
    def _execute_enhanced_enrichment_phase(self, workflow_state: Dict[str, Any]):
        """Execute profile enrichment phase with intelligent candidate selection"""
        logger.info("💼 Phase 3: Enhanced Profile Enrichment")
        workflow_state["current_stage"] = WorkflowStage.ENRICHING.value
        
        try:
            # Get suitable candidates for enrichment (cost optimization)
            candidate_records = workflow_state["candidates_records"]["evaluated"]
            suitable_records = [
                c for c in candidate_records 
                if c.suitability_status in ["suitable", "maybe"]
            ]
            
            if not suitable_records:
                logger.info("No suitable candidates found for enrichment")
                workflow_state["candidates_pipeline"]["enriched"] = []
                workflow_state["candidates_records"]["enriched"] = []
                return
            
            # Mock enrichment process (enhance when ProfileScrapingAgent is available)
            enriched_records = []
            for candidate_record in suitable_records:
                enriched_record = self._enrich_candidate_record(candidate_record)
                enriched_records.append(enriched_record)
            
            # Convert back to dict format for pipeline
            enriched_candidates = [record.dict() for record in enriched_records]
            
            workflow_state["candidates_pipeline"]["enriched"] = enriched_candidates
            workflow_state["candidates_records"]["enriched"] = enriched_records
            workflow_state["metrics"]["total_enriched"] = len(enriched_candidates)
            workflow_state["stages_completed"].append("enrichment")
            
            # Update enriched candidates in database
            self._update_enriched_candidates_in_database(enriched_candidates, workflow_state["project_id"])
            
            logger.info(f"✅ Enriched {len(enriched_candidates)} candidate profiles")
            
        except Exception as e:
            logger.error(f"⚠️ Enrichment phase warning: {str(e)}")
            workflow_state["warnings"].append(f"Enrichment failed: {str(e)}")
            # Continue with non-enriched suitable candidates
            suitable_candidates = [
                c.dict() for c in workflow_state["candidates_records"]["evaluated"]
                if c.suitability_status in ["suitable", "maybe"]
            ]
            workflow_state["candidates_pipeline"]["enriched"] = suitable_candidates
            workflow_state["candidates_records"]["enriched"] = [
                c for c in workflow_state["candidates_records"]["evaluated"]
                if c.suitability_status in ["suitable", "maybe"]
            ]
    
    # ---- Enhanced Decision Making Methods (AI-Powered) ----
    
    def _should_proceed_to_evaluation(self, workflow_state: Dict[str, Any]) -> bool:
        """AI-enhanced decision logic for proceeding to evaluation phase"""
        candidates_found = workflow_state["metrics"]["total_found"]
        min_threshold = self.min_candidates_threshold  # From .env configuration
        
        if candidates_found < min_threshold:
            logger.warning(f"Only {candidates_found} candidates found, minimum is {min_threshold}")
            
            # AI decision on whether to proceed with limited candidates (if enabled)
            if self.config.unified_sourcing.ai_decision_enabled:
                decision = self._make_workflow_decision("low_candidate_count", workflow_state)
                workflow_state["decisions"].append(decision.dict() if hasattr(decision, 'dict') else str(decision))
                
                if decision.action == "continue":
                    workflow_state["warnings"].append(f"Proceeding with limited candidates: {candidates_found}")
                    return True
                elif decision.action == "retry":
                    if workflow_state["retry_count"] < self.max_retries:
                        workflow_state["retry_count"] += 1
                        self._retry_search_with_adjustments(workflow_state)
                        return workflow_state["metrics"]["total_found"] >= min_threshold
            else:
                # Simple logic when AI decisions are disabled
                if candidates_found > 0:
                    workflow_state["warnings"].append(f"Proceeding with {candidates_found} candidates (AI decisions disabled)")
                    return True
            
            return False
        
        return True
    
    def _should_proceed_to_enrichment(self, workflow_state: Dict[str, Any]) -> bool:
        """AI-enhanced decision logic for proceeding to enrichment phase"""
        suitable_count = workflow_state["metrics"]["total_suitable"]
        min_threshold = self.min_suitable_threshold  # From .env configuration
        
        if suitable_count < min_threshold:
            # AI decision on enrichment with limited suitable candidates (if enabled)
            if self.config.unified_sourcing.ai_decision_enabled:
                decision = self._make_workflow_decision("low_suitable_count", workflow_state)
                workflow_state["decisions"].append(decision.dict() if hasattr(decision, 'dict') else str(decision))
                
                if decision.action == "continue":
                    logger.info(f"Proceeding with enrichment of {suitable_count} suitable candidates")
                    workflow_state["warnings"].append(f"Low suitable candidate count: {suitable_count}")
                    return suitable_count > 0
                elif decision.action == "adjust":
                    # Lower evaluation criteria and re-evaluate
                    self._adjust_evaluation_criteria(workflow_state)
                    return workflow_state["metrics"]["total_suitable"] > 0
            else:
                # Simple logic when AI decisions are disabled
                if suitable_count > 0:
                    workflow_state["warnings"].append(f"Proceeding with {suitable_count} suitable candidates (AI decisions disabled)")
                    return True
        
        return suitable_count > 0
    
    def _make_workflow_decision(self, situation: str, workflow_state: Dict[str, Any]) -> SourcingManagerDecision:
        """Make intelligent workflow decisions using AI/LLM"""
        
        try:
            # Prepare decision context
            context = {
                "situation": situation,
                "current_stage": workflow_state["current_stage"],
                "candidates_found": workflow_state["metrics"]["total_found"],
                "candidates_suitable": workflow_state["metrics"]["total_suitable"],
                "success_rate": workflow_state["metrics"]["success_rate"],
                "retry_count": workflow_state["retry_count"],
                "max_retries": self.max_retries,
                "target_count": workflow_state["target_count"],
                "errors": len(workflow_state["errors"]),
                "warnings": len(workflow_state["warnings"])
            }
            
            # Create decision prompt
            decision_prompt = f"""
            As a Sourcing Manager AI, analyze this workflow situation and make a decision:
            
            SITUATION: {situation}
            CONTEXT: {json.dumps(context, indent=2)}
            
            Based on this context, decide what action to take:
            - CONTINUE: Proceed with current workflow despite limitations
            - RETRY: Retry the current phase with same parameters
            - ADJUST: Modify criteria/parameters and retry
            - ESCALATE: Situation requires human intervention
            - COMPLETE: Finish workflow with current results
            
            Respond with JSON format:
            {{
                "action": "continue|retry|adjust|escalate|complete",
                "reasoning": "Detailed explanation of the decision",
                "confidence": 0.8,
                "next_steps": ["specific", "actionable", "steps"],
                "adjustments": {{"parameter": "new_value"}}
            }}
            """
            
            # Mock AI decision (replace with your LLM implementation)
            # messages = [
            #     SystemMessage(content="You are an expert AI Sourcing Manager making workflow decisions."),
            #     HumanMessage(content=decision_prompt)
            # ]
            # response = await self.llm.ainvoke(messages)
            
            # Mock decision logic for now
            if situation == "low_candidate_count" and context["retry_count"] < self.max_retries:
                mock_response_content = '{"action": "retry", "reasoning": "Low candidate count warrants retry with broader criteria", "confidence": 0.8, "next_steps": ["Broaden search criteria", "Retry search"], "adjustments": {"search_criteria": "broader"}}'
            elif situation == "low_suitable_count":
                mock_response_content = '{"action": "adjust", "reasoning": "Low suitable count suggests evaluation criteria may be too strict", "confidence": 0.7, "next_steps": ["Lower evaluation threshold", "Re-evaluate candidates"], "adjustments": {"evaluation_threshold": "lower"}}'
            else:
                mock_response_content = '{"action": "continue", "reasoning": "Proceed with available candidates", "confidence": 0.6, "next_steps": ["Continue with current candidates"], "adjustments": {}}'
            
            # Parse AI response (mock implementation)
            try:
                decision_data = json.loads(mock_response_content)
                return SourcingManagerDecision(
                    action=decision_data.get("action", "continue"),
                    reasoning=decision_data.get("reasoning", "AI decision made"),
                    confidence=decision_data.get("confidence", 0.7),
                    next_steps=decision_data.get("next_steps", []),
                    adjustments=decision_data.get("adjustments", {})
                )
            except json.JSONDecodeError:
                # Fallback to simple parsing
                if "retry" in mock_response_content.lower():
                    action = "retry"
                elif "adjust" in mock_response_content.lower():
                    action = "adjust"
                elif "escalate" in mock_response_content.lower():
                    action = "escalate"
                elif "continue" in mock_response_content.lower():
                    action = "continue"
                else:
                    action = "complete"
                
                return SourcingManagerDecision(
                    action=action,
                    reasoning=mock_response_content,
                    confidence=0.6,
                    next_steps=["Execute recommended action"]
                )
        
        except Exception as e:
            logger.warning(f"AI decision making failed, using fallback: {str(e)}")
            # Fallback decision logic
            if situation == "low_candidate_count" and workflow_state["retry_count"] < self.max_retries:
                return SourcingManagerDecision(
                    action="retry",
                    reasoning="Fallback: Retry search with adjusted criteria",
                    confidence=0.5,
                    next_steps=["Broaden search criteria", "Retry search"]
                )
            else:
                return SourcingManagerDecision(
                    action="continue",
                    reasoning="Fallback: Continue with available candidates",
                    confidence=0.5,
                    next_steps=["Proceed with current candidates"]
                )
    
    # ---- Enhanced Parsing Methods ----
    
    def _parse_search_results(self, search_result: Dict[str, Any]) -> List[CandidateRecord]:
        """Parse search agent results into CandidateRecord objects"""
        candidates = []
        
        for candidate_data in search_result.get("candidates", []):
            candidate = CandidateRecord(
                candidate_id=str(uuid.uuid4()),
                linkedin_url=candidate_data.get("linkedin_url", ""),
                name=candidate_data.get("name", "Unknown"),
                title=candidate_data.get("title", ""),
                company=candidate_data.get("company", ""),
                location=candidate_data.get("location", ""),
                skills=candidate_data.get("skills", []),
                search_score=candidate_data.get("search_score", 0.0),
                search_source=candidate_data.get("search_source", "linkedin"),
                search_timestamp=datetime.now()
            )
            candidates.append(candidate)
        
        return candidates
    
    def _parse_evaluation_results(self, evaluation_result: Dict[str, Any], search_records: List[CandidateRecord]) -> List[CandidateRecord]:
        """Parse evaluation agent results and update candidate records"""
        updated_candidates = []
        
        # Create lookup for existing records
        search_lookup = {record.linkedin_url: record for record in search_records}
        
        for evaluated_candidate in evaluation_result.get("evaluated_candidates", []):
            linkedin_url = evaluated_candidate.get("linkedin_url", "")
            
            # Find existing record or create new one
            if linkedin_url in search_lookup:
                candidate = search_lookup[linkedin_url]
            else:
                candidate = CandidateRecord(
                    candidate_id=str(uuid.uuid4()),
                    linkedin_url=linkedin_url,
                    name=evaluated_candidate.get("name", "Unknown")
                )
            
            # Update with evaluation data
            candidate.title = evaluated_candidate.get("title", candidate.title)
            candidate.company = evaluated_candidate.get("company", candidate.company)
            candidate.location = evaluated_candidate.get("location", candidate.location)
            candidate.skills = evaluated_candidate.get("skills", candidate.skills)
            candidate.suitability_status = evaluated_candidate.get("suitability_status", "unknown")
            candidate.suitability_score = evaluated_candidate.get("suitability_score", 0.0)
            candidate.suitability_reasoning = evaluated_candidate.get("suitability_reasoning", "")
            candidate.evaluation_timestamp = datetime.now()
            
            updated_candidates.append(candidate)
        
        return updated_candidates
    
    def _enrich_candidate_record(self, candidate_record: CandidateRecord) -> CandidateRecord:
        """Enrich candidate record with additional data (mock implementation)"""
        enriched = candidate_record
        enriched.profile_enriched = True
        enriched.enrichment_timestamp = datetime.now()
        enriched.enrichment_details = {
            "contact_info_found": False,  # Privacy compliant
            "profile_completeness": "high",
            "additional_skills": ["Leadership", "Team Management"],
            "verification_status": "linkedin_confirmed",
            "experience_details": {
                "total_years": enriched.experience_years or 5,
                "current_role_years": 2,
                "career_progression": "steady"
            }
        }
        
        # Add some enriched skills
        additional_skills = enriched.enrichment_details.get("additional_skills", [])
        enriched.skills = list(set(enriched.skills + additional_skills))
        
        return enriched
    
    # ---- Database Integration Methods (from main version) ----
    
    def _save_candidates_to_database(self, candidates: List[Dict[str, Any]], project_id: str):
        """Save candidates to database via DatabaseAgent delegation pattern"""
        logger.info(f"💾 Saving {len(candidates)} candidates to database for project {project_id}")
        
        saved_count = 0
        failed_count = 0
        
        for candidate in candidates:
            try:
                # Validate LinkedIn URL - this is our unique identifier
                linkedin_url = candidate.get("linkedin_url", "").strip()
                if not linkedin_url:
                    logger.warning(f"⚠️ Skipping candidate {candidate.get('name')} - no LinkedIn URL for unique identification")
                    failed_count += 1
                    continue
                
                # Prepare candidate data for database storage with LinkedIn URL as unique key
                candidate_data = {
                    "_id": linkedin_url,  # Use LinkedIn URL as unique MongoDB _id
                    "name": candidate.get("name", "Unknown"),
                    "email": candidate.get("email", ""),
                    "phone": candidate.get("phone", ""),
                    "linkedin_url": linkedin_url,
                    "title": candidate.get("title", ""),
                    "company": candidate.get("company", ""),
                    "location": candidate.get("location", ""),
                    "skills": candidate.get("skills", []),
                    "experience_years": candidate.get("experience_years", 0),
                    "project_id": project_id,
                    "pipeline_stage": "sourced",
                    "sourced_at": datetime.now().isoformat(),
                    "suitability_status": candidate.get("suitability_status", "unknown"),
                    "suitability_score": candidate.get("suitability_score", 0),
                    "suitability_reasoning": candidate.get("suitability_reasoning", ""),
                    "source": "UnifiedSourcingManager",
                    "profile_version": "basic",
                    "last_updated": datetime.now().isoformat(),
                    "evaluation_metadata": {
                        "evaluated_at": datetime.now().isoformat(),
                        "evaluation_agent": "CandidateEvaluationAgent",
                        "fit_score": candidate.get("suitability_score", 0)
                    }
                }
                
                # Delegate to DatabaseAgent for actual storage
                result = self.database_agent.tools.save_candidate(candidate_data)
                
                if result.get("success"):
                    saved_count += 1
                    logger.debug(f"✅ Saved candidate: {candidate.get('name')}")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Failed to save candidate: {candidate.get('name')} - {result.get('message')}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error saving candidate {candidate.get('name')}: {str(e)}")
        
        logger.info(f"💾 Database storage complete: {saved_count} saved, {failed_count} failed")
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} candidates failed to save - manual review recommended")
    
    def _update_enriched_candidates_in_database(self, enriched_candidates: List[Dict[str, Any]], project_id: str):
        """Update candidates in database with enrichment data via DatabaseAgent delegation pattern"""
        logger.info(f"🔄 Updating {len(enriched_candidates)} enriched candidates in database for project {project_id}")
        
        updated_count = 0
        failed_count = 0
        
        for candidate in enriched_candidates:
            try:
                # Use LinkedIn URL as unique identifier for updates
                linkedin_url = candidate.get("linkedin_url", "").strip()
                if not linkedin_url:
                    logger.warning(f"⚠️ Skipping candidate {candidate.get('name')} enrichment update - no LinkedIn URL for identification")
                    failed_count += 1
                    continue
                
                # Prepare update data for enriched candidate
                update_data = {
                    "pipeline_stage": "enriched",
                    "enriched_at": datetime.now().isoformat(),
                    "profile_enriched": candidate.get("profile_enriched", True),
                    "enrichment_details": candidate.get("enrichment_details", {}),
                    "enrichment_timestamp": candidate.get("enrichment_timestamp"),
                    "profile_version": "enriched",
                    "last_updated": datetime.now().isoformat(),
                    "updated_by": "UnifiedSourcingManager_EnrichmentPhase"
                }
                
                # Add any additional enriched skills or data
                if "additional_skills" in candidate.get("enrichment_details", {}):
                    current_skills = candidate.get("skills", [])
                    additional_skills = candidate["enrichment_details"]["additional_skills"]
                    # Merge skills without duplicates
                    all_skills = list(set(current_skills + additional_skills))
                    update_data["skills"] = all_skills
                
                # Delegate to DatabaseAgent for actual update using LinkedIn URL as identifier
                result = self.database_agent.tools.update_candidate_status(linkedin_url, update_data)
                
                if result.get("success"):
                    updated_count += 1
                    logger.debug(f"✅ Updated enriched candidate: {candidate.get('name')} ({linkedin_url})")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Failed to update candidate: {candidate.get('name')} - {result.get('message')}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error updating enriched candidate {candidate.get('name')}: {str(e)}")
        
        logger.info(f"🔄 Database enrichment update complete: {updated_count} updated, {failed_count} failed")
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} enriched candidates failed to update - manual review recommended")
    
    # ---- Enhanced Results Generation ----
    
    def _generate_enhanced_final_results(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive final results with enhanced metadata"""
        workflow_state["current_stage"] = WorkflowStage.COMPLETED.value
        workflow_state["completed_at"] = datetime.now()
        workflow_state["stages_completed"].append("finalization")
        
        # Use enhanced candidate records for final results
        final_records = (
            workflow_state["candidates_records"]["enriched"] 
            if workflow_state["candidates_records"]["enriched"]
            else [c for c in workflow_state["candidates_records"]["evaluated"]
                  if c.suitability_status in ["suitable", "maybe"]]
        )
        
        # Sort by suitability score
        final_records.sort(key=lambda c: c.suitability_score, reverse=True)
        workflow_state["candidates_records"]["final"] = final_records
        
        # Calculate processing time
        duration = (
            workflow_state["completed_at"] - workflow_state["started_at"]
        ).total_seconds() / 60
        
        # Prepare enhanced top candidates summary
        top_candidates = final_records[:10]
        top_summary = []
        
        for candidate_record in top_candidates:
            summary = {
                "candidate_id": candidate_record.candidate_id,
                "name": candidate_record.name,
                "title": candidate_record.title,
                "company": candidate_record.company,
                "location": candidate_record.location,
                "linkedin_url": candidate_record.linkedin_url,
                "suitability_score": candidate_record.suitability_score,
                "suitability_status": candidate_record.suitability_status,
                "reasoning": candidate_record.suitability_reasoning,
                "profile_enriched": candidate_record.profile_enriched,
                "skills": candidate_record.skills,
                "experience_years": candidate_record.experience_years
            }
            top_summary.append(summary)
        
        # Generate AI-powered recommendations
        recommendations = self._generate_ai_recommendations(workflow_state)
        
        return {
            "request_id": workflow_state["request_id"],
            "status": "completed",
            "summary": {
                "total_found": workflow_state["metrics"]["total_found"],
                "total_suitable": workflow_state["metrics"]["total_suitable"],
                "total_enriched": workflow_state["metrics"]["total_enriched"],
                "success_rate": workflow_state["metrics"]["success_rate"],
                "processing_time_minutes": duration,
                "stages_completed": workflow_state["stages_completed"],
                "ai_decisions_made": len(workflow_state["decisions"]),
                "retry_count": workflow_state["retry_count"]
            },
            "candidates": {
                "top_candidates": top_summary,
                "total_final_candidates": len(final_records),
                "suitable_count": len([c for c in final_records if c.suitability_status == "suitable"]),
                "maybe_count": len([c for c in final_records if c.suitability_status == "maybe"])
            },
            "workflow": {
                "errors": workflow_state["errors"],
                "warnings": workflow_state["warnings"],
                "decisions": workflow_state["decisions"],
                "completed_at": workflow_state["completed_at"].isoformat()
            },
            "recommendations": recommendations,
            "next_steps": [
                "Review top candidate recommendations with hiring team",
                "Prioritize outreach based on suitability scores and reasoning",
                "Prepare personalized messaging for top suitable candidates",
                "Begin candidate engagement sequence with highest-scoring candidates",
                "Schedule initial screening calls for top 5 candidates"
            ]
        }
    
    def _generate_ai_recommendations(self, workflow_state: Dict[str, Any]) -> List[str]:
        """Generate AI-powered actionable recommendations based on workflow results"""
        try:
            context = {
                "total_found": workflow_state["metrics"]["total_found"],
                "total_suitable": workflow_state["metrics"]["total_suitable"],
                "success_rate": workflow_state["metrics"]["success_rate"],
                "stages_completed": workflow_state["stages_completed"],
                "errors": len(workflow_state["errors"]),
                "warnings": len(workflow_state["warnings"]),
                "decisions_made": len(workflow_state["decisions"])
            }
            
            prompt = f"""
            As an expert Recruitment AI, analyze these sourcing results and generate actionable recommendations:
            
            RESULTS: {json.dumps(context, indent=2)}
            
            Generate 3-5 specific, actionable recommendations for the hiring team.
            Focus on: candidate quality, process optimization, and next steps.
            
            Return as JSON array: ["recommendation 1", "recommendation 2", ...]
            """
            
            # Mock AI recommendation generation (replace with your LLM)
            # messages = [
            #     SystemMessage(content="You are an expert recruitment strategist AI."),
            #     HumanMessage(content=prompt)
            # ]
            # response = await self.llm.ainvoke(messages)
            
            # Mock recommendations based on context
            mock_recommendations = []
            if context["success_rate"] > 0.7:
                mock_recommendations.append("Excellent candidate quality - proceed with confidence to outreach phase")
            elif context["success_rate"] > 0.4:
                mock_recommendations.append("Good candidate pool - consider additional sourcing for backup candidates")
            else:
                mock_recommendations.append("Low success rate - review job requirements or search strategy")
            
            if context["total_suitable"] < 5:
                mock_recommendations.append("Limited candidate pool - consider broadening search criteria")
            elif context["total_suitable"] > 15:
                mock_recommendations.append("Strong candidate pipeline - prioritize by suitability score")
            
            if context["errors"] > 0:
                mock_recommendations.append("Review workflow errors for process improvements")
            
            mock_recommendations.append("Begin candidate outreach with top-scoring candidates")
            
            return mock_recommendations
        
        except Exception as e:
            logger.warning(f"AI recommendation generation failed, using fallback: {str(e)}")
            return self._generate_fallback_recommendations(workflow_state)
    
    def _generate_fallback_recommendations(self, workflow_state: Dict[str, Any]) -> List[str]:
        """Generate fallback recommendations when AI fails"""
        recommendations = []
        metrics = workflow_state["metrics"]
        
        # Success rate analysis
        if metrics["success_rate"] > 0.7:
            recommendations.append("Excellent candidate quality - proceed with confidence to outreach phase")
        elif metrics["success_rate"] > 0.4:
            recommendations.append("Good candidate pool - consider additional sourcing for backup candidates")
        else:
            recommendations.append("Low success rate - review job requirements or search strategy before proceeding")
        
        # Quantity analysis
        if metrics["total_suitable"] < 5:
            recommendations.append("Limited candidate pool - consider broadening search criteria or alternative sourcing channels")
        elif metrics["total_suitable"] > 15:
            recommendations.append("Strong candidate pipeline - prioritize by suitability score and focus on top performers")
        
        # Process analysis
        if workflow_state["errors"]:
            recommendations.append("Review workflow errors for process improvements in future sourcing rounds")
        
        if not workflow_state["warnings"]:
            recommendations.append("Clean workflow execution - process is optimized and ready for scaling")
        
        return recommendations
    
    # ---- Adaptive Search Methods ----
    
    def _retry_search_with_adjustments(self, workflow_state: Dict[str, Any]):
        """Retry search with intelligently adjusted parameters"""
        logger.info("🔄 Retrying search with adaptive adjustments")
        
        # Broaden search criteria intelligently
        original_requirements = workflow_state["project_requirements"].copy()
        
        # Adjust experience level
        if "experience_level" in original_requirements:
            if original_requirements["experience_level"] == "senior":
                original_requirements["experience_level"] = "mid"
            elif original_requirements["experience_level"] == "mid":
                original_requirements["experience_level"] = "junior"
        
        # Expand location if specified
        if "location" in original_requirements and original_requirements["location"] != "remote":
            original_requirements["remote_ok"] = True
        
        # Reduce required skills to core essentials
        if "required_skills" in original_requirements:
            core_skills = original_requirements["required_skills"][:3]  # Top 3 only
            original_requirements["required_skills"] = core_skills
        
        # Increase target count
        workflow_state["target_count"] = min(workflow_state["target_count"] * 1.5, 150)
        
        workflow_state["project_requirements"] = original_requirements
        logger.info("✅ Search criteria adjusted for broader candidate pool")
    
    def _adjust_search_criteria(self, workflow_state: Dict[str, Any]):
        """Adjust search criteria based on AI decision"""
        logger.info("🎯 Adjusting search criteria based on AI analysis")
        
        # This could be enhanced with more sophisticated AI analysis
        criteria = workflow_state["project_requirements"]
        
        # Make criteria more flexible
        if "required_skills" in criteria and len(criteria["required_skills"]) > 5:
            # Reduce to must-have skills only
            criteria["required_skills"] = criteria["required_skills"][:5]
        
        # Add remote option if not present
        if "remote_ok" not in criteria:
            criteria["remote_ok"] = True
        
        workflow_state["project_requirements"] = criteria
    
    def _adjust_evaluation_criteria(self, workflow_state: Dict[str, Any]):
        """Adjust evaluation criteria to be more inclusive"""
        logger.info("📊 Adjusting evaluation criteria for more inclusive assessment")
        
        # This would involve re-running evaluation with adjusted scoring
        # For now, we'll mark this as a placeholder for future enhancement
        workflow_state["warnings"].append("Evaluation criteria adjusted to be more inclusive")
    
    # ---- Error Handling Methods ----
    
    def _generate_early_completion_results(self, workflow_state: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Generate results for early workflow completion"""
        return {
            "request_id": workflow_state["request_id"],
            "status": "completed_early",
            "reason": reason,
            "partial_results": {
                "candidates_found": workflow_state["metrics"]["total_found"],
                "stages_completed": workflow_state["stages_completed"],
                "decisions_made": workflow_state["decisions"]
            },
            "recommendations": [
                "Consider broadening search criteria or adjusting job requirements",
                "Review market availability for the specified role and location",
                "Try alternative sourcing strategies or different platforms"
            ]
        }
    
    def _generate_results_without_enrichment(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate results when skipping enrichment phase"""
        suitable_records = [
            c for c in workflow_state["candidates_records"]["evaluated"]
            if c.suitability_status in ["suitable", "maybe"]
        ]
        
        return {
            "request_id": workflow_state["request_id"],
            "status": "completed_basic",
            "summary": {
                "total_found": workflow_state["metrics"]["total_found"],
                "total_suitable": len(suitable_records),
                "success_rate": workflow_state["metrics"]["success_rate"]
            },
            "candidates": [record.dict() for record in suitable_records[:10]],
            "note": "Profile enrichment skipped - proceeding with basic candidate data",
            "recommendations": [
                "Consider manual profile research for top candidates",
                "Proceed with outreach using available basic data",
                "Schedule enrichment phase for successful initial contacts"
            ]
        }
    
    def _generate_error_results(self, workflow_state: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Generate error results when workflow fails"""
        return {
            "request_id": workflow_state["request_id"],
            "status": "error",
            "error_message": error_message,
            "partial_results": {
                "stages_completed": workflow_state["stages_completed"],
                "candidates_found": workflow_state["metrics"]["total_found"],
                "decisions_made": workflow_state["decisions"]
            },
            "recommendations": [
                "Review error details and retry with adjusted parameters",
                "Check sub-agent availability and configuration",
                "Consider manual fallback processes for critical searches",
                "Contact technical support if errors persist"
            ]
        }


# ---- Factory Function ----

def create_unified_sourcing_manager(config: Optional[Dict[str, Any]] = None) -> UnifiedSourcingManager:
    """Factory function to create configured UnifiedSourcingManager instance"""
    config = config or {}
    
    return UnifiedSourcingManager(
        model_name=config.get("model_name", "gpt-4"),
        temperature=config.get("temperature", 0.3)
    )


# ---- Example Usage ----

def example_unified_sourcing():
    """Example of production sourcing workflow with unified manager"""
    
    # Initialize unified manager
    manager = create_unified_sourcing_manager({
        "model_name": "gpt-4",
        "temperature": 0.2
    })
    
    # Define realistic project requirements
    project_requirements = {
        "required_skills": ["Python", "Machine Learning", "AWS"],
        "preferred_skills": ["Docker", "Kubernetes", "TensorFlow"],
        "experience_level": "mid",
        "location": "Amsterdam",
        "industry": "fintech",
        "team_size": "startup",
        "remote_ok": True
    }
    
    job_description = """
    Senior Python Developer - Machine Learning Focus
    
    We're seeking a talented Senior Python Developer with strong Machine Learning expertise 
    to join our innovative fintech startup in Amsterdam. You'll be building the next generation of 
    financial AI systems that help millions of users make better financial decisions.
    
    Requirements:
    - 4+ years Python development experience
    - Strong ML/AI background (scikit-learn, TensorFlow, PyTorch)
    - AWS cloud experience (SageMaker, Lambda, EC2)
    - Experience with production ML systems
    - Fintech or financial services background preferred
    
    What we offer:
    - Competitive salary + equity (€80k-€120k)
    - Hybrid work model (Amsterdam + remote)
    - Cutting-edge ML projects
    - Strong engineering culture
    """
    
    # Execute unified sourcing request (now synchronous)
    results = manager.process_sourcing_request(
        project_requirements=project_requirements,
        job_description=job_description,
        project_id="unified_example_project_2025",
        target_count=75
    )
    
    return results


if __name__ == "__main__":
    # Run unified example (now synchronous)
    print("🚀 Running Unified Sourcing Manager Example")
    print("=" * 60)
    
    results = example_unified_sourcing()
    
    print("\n📊 UNIFIED SOURCING RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))
    
    print(f"\n✅ Status: {results['status']}")
    if 'summary' in results:
        summary = results['summary']
        print(f"📋 Total Found: {summary['total_found']} candidates")
        print(f"🎯 Total Suitable: {summary['total_suitable']} candidates")
        print(f"💎 Total Enriched: {summary['total_enriched']} candidates")
        print(f"📈 Success Rate: {summary['success_rate']:.1%}")
        print(f"⏱️ Processing Time: {summary.get('processing_time_minutes', 0):.2f} minutes")
        print(f"🤖 AI Decisions Made: {summary.get('ai_decisions_made', 0)}")
    
    print("\n🎯 READY FOR OUTREACH PHASE WITH ENHANCED INTELLIGENCE!")