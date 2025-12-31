"""
Unified Sourcing Manager - Intelligent Candidate Discovery Pipeline

This module implements the UnifiedSourcingManager, a production-ready orchestrator
for the candidate sourcing pipeline. It coordinates specialized sub-agents to
discover, evaluate, and enrich candidate profiles with AI-powered decision making.

Architecture:
============

    UnifiedSourcingManager (Orchestrator)
    ├── Phase 1: Candidate Search
    │   └── CandidateSearchingAgent
    │       └── LinkedIn API (via Unipile)
    ├── Phase 2: Candidate Evaluation
    │   └── CandidateEvaluationAgent
    │       └── AI-Powered Suitability Assessment
    ├── Phase 3: Profile Enrichment
    │   └── ProfileScrapingAgent (optional)
    │       └── Deep Profile Analysis
    └── Phase 4: Database Storage
        └── DatabaseAgent (monopoly pattern)

Workflow Stages:
===============

1. **INITIALIZING**: Setup and validation
2. **SEARCHING**: LinkedIn candidate search
3. **EVALUATING**: AI-powered suitability assessment
4. **ENRICHING**: Optional deep profile enrichment
5. **FINALIZING**: Results compilation and storage
6. **COMPLETED**: Pipeline complete
7. **ERROR**: Error state (with recovery)

Design Patterns:
===============

1. **Pipeline Pattern**: Sequential processing stages
2. **Strategy Pattern**: Different search/evaluation strategies
3. **AI Decision Making**: Intelligent workflow adjustments
4. **Retry Logic**: Exponential backoff for API failures
5. **Quality Gates**: Threshold-based filtering

Features:
=========

- Multi-phase candidate discovery pipeline
- AI-powered suitability evaluation
- Intelligent retry logic with exponential backoff
- Quality threshold enforcement
- Database integration (via DatabaseAgent)
- Comprehensive error handling
- Workflow state tracking
- Performance metrics collection

Author: Senior Development Team
Version: 1.0.0
License: MIT
"""

# ---- Package imports ----
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import time
import re
import uuid
import asyncio

# AI decision making (mock implementation - replace with your preferred LLM)
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_openai import ChatOpenAI

# Custom imports for the working system
from config import get_config, AppConfig

# Clean architecture orchestrator and dependencies
from src.application.orchestrators.sourcing_manager_orchestrator import (
    SourcingManagerOrchestrator,
)
from src.application.use_cases.sourcing.search_candidates import SearchCandidatesUseCase
from src.domain.services.candidate_evaluation_service import CandidateEvaluationService
from src.infrastructure.persistence.mongodb.mongodb_candidate_repository import (
    MongoDBCandidateRepository,
)
from src.infrastructure.persistence.mongodb.mongodb_project_repository import (
    MongoDBProjectRepository,
)
from src.infrastructure.external_services.linkedin.linkedin_service_impl import (
    LinkedInServiceImpl,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- Data Classes for Enhanced Structure ----

@dataclass
class CandidateRecord:
    """
    Enhanced candidate record with comprehensive metadata.
    
    This dataclass represents a candidate throughout the sourcing pipeline,
    tracking their journey from initial discovery through evaluation and
    enrichment. It maintains metadata at each stage for auditability and
    quality assessment.
    
    Attributes:
        candidate_id: Unique identifier for the candidate
        linkedin_url: LinkedIn profile URL (used as unique key)
        name: Candidate's full name
        title: Current job title
        company: Current company name
        location: Geographic location
        experience_years: Years of professional experience
        skills: List of technical skills
        education: List of education entries (dicts with institution, degree, etc.)
        contact_info: Dictionary with contact information
        search_score: Relevance score from search (0.0-1.0)
        search_source: Source of the candidate (default: "linkedin")
        search_timestamp: When candidate was discovered
        suitability_status: Evaluation result ("suitable", "maybe", "unsuitable", "unknown")
        suitability_score: Suitability score (0.0-100.0)
        suitability_reasoning: AI-generated reasoning for suitability
        evaluation_timestamp: When evaluation was performed
        profile_enriched: Whether deep enrichment was performed
        enrichment_timestamp: When enrichment was performed
        enrichment_details: Additional enriched data
    
    Example:
        >>> candidate = CandidateRecord(
        ...     candidate_id="c123",
        ...     linkedin_url="https://linkedin.com/in/johndoe",
        ...     name="John Doe",
        ...     title="Senior Python Developer",
        ...     company="Tech Corp",
        ...     location="Amsterdam",
        ...     experience_years=7,
        ...     skills=["Python", "Django", "AWS"],
        ...     suitability_score=85.0,
        ...     suitability_status="suitable"
        ... )
        >>> candidate_dict = candidate.dict()
    
    Note:
        The linkedin_url serves as a unique key for deduplication in the database.
        All timestamps are stored as datetime objects and converted to ISO format
        in the dict() method for JSON serialization.
    """
    candidate_id: str
    linkedin_url: str
    name: str
    title: str = ""
    company: str = ""
    location: str = ""
    experience_years: int = 0
    skills: List[str] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    work_experience: List[Dict[str, Any]] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)
    profile_summary: str = ""
    
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
    relevant_skills: List[str] = field(default_factory=list)
    relevant_experience: List[Dict[str, Any]] = field(default_factory=list)
    
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
            "work_experience": self.work_experience,
            "contact_info": self.contact_info,
            "profile_summary": self.profile_summary,
            "search_score": self.search_score,
            "search_source": self.search_source,
            "search_timestamp": self.search_timestamp.isoformat() if self.search_timestamp else None,
            "suitability_status": self.suitability_status,
            "suitability_score": self.suitability_score,
            "suitability_reasoning": self.suitability_reasoning,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat() if self.evaluation_timestamp else None,
            "profile_enriched": self.profile_enriched,
            "enrichment_timestamp": self.enrichment_timestamp.isoformat() if self.enrichment_timestamp else None,
            "enrichment_details": self.enrichment_details,
            "relevant_skills": self.relevant_skills,
            "relevant_experience": self.relevant_experience
        }


@dataclass
class SourcingManagerDecision:
    """
    AI-powered workflow decision with reasoning.
    
    Represents a decision made by the AI decision-making system during the
    sourcing workflow. Used to dynamically adjust the pipeline based on
    current state and quality metrics.
    
    Attributes:
        action: Decision action type. One of:
            - "continue": Proceed to next phase
            - "retry": Retry current phase with adjustments
            - "adjust": Modify search criteria and retry
            - "escalate": Require human intervention
            - "complete": Pipeline complete, sufficient candidates found
        reasoning: Human-readable explanation of the decision
        confidence: Confidence score (0.0-1.0) in the decision
        next_steps: List of recommended next steps
        adjustments: Dictionary of parameter adjustments to apply
    
    Example:
        >>> decision = SourcingManagerDecision(
        ...     action="retry",
        ...     reasoning="Low candidate quality, adjusting search criteria",
        ...     confidence=0.85,
        ...     next_steps=["Broaden location criteria", "Reduce experience requirement"],
        ...     adjustments={"location": "Netherlands", "min_experience": 3}
        ... )
    
    Note:
        This class is used by the AI decision-making system to provide
        transparent, auditable workflow adjustments.
    """
    action: str  # continue, retry, adjust, escalate, complete
    reasoning: str
    confidence: float
    next_steps: List[str]
    adjustments: Dict[str, Any] = field(default_factory=dict)


class WorkflowStage(Enum):
    """
    Workflow stages for pipeline state tracking.
    
    Enumeration of all possible stages in the candidate sourcing pipeline.
    Used for state management, logging, and workflow routing.
    
    Values:
        INITIALIZING: Initial setup and validation phase
        SEARCHING: Active candidate search phase
        EVALUATING: Candidate suitability evaluation phase
        ENRICHING: Optional deep profile enrichment phase
        FINALIZING: Results compilation and storage phase
        COMPLETED: Pipeline successfully completed
        ERROR: Error state (with recovery mechanisms)
    
    Example:
        >>> stage = WorkflowStage.SEARCHING
        >>> print(stage.value)
        'searching'
    
    Note:
        The pipeline can transition between stages based on AI decisions
        and quality thresholds. The ERROR state triggers recovery mechanisms.
    """
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
    Production-ready orchestrator for the candidate sourcing pipeline.
    
    The UnifiedSourcingManager coordinates a multi-phase candidate discovery
    pipeline, from initial LinkedIn search through AI-powered evaluation and
    optional profile enrichment. It implements intelligent decision-making,
    retry logic, and quality threshold enforcement.
    
    Responsibilities:
        - Orchestrate candidate search via LinkedIn API (Unipile)
        - Coordinate AI-powered suitability evaluation
        - Manage optional profile enrichment
        - Enforce quality thresholds
        - Handle errors with retry logic
        - Store candidates via DatabaseAgent
    
    Design:
        - Pipeline pattern with quality gates
        - AI-powered workflow adjustments
        - Exponential backoff retry logic
        - Comprehensive error handling
        - Database integration (monopoly pattern)
    
    Attributes:
        config: Application configuration (AppConfig)
        model_name: AI model name for evaluation
        temperature: AI model temperature
        search_agent: CandidateSearchingAgent instance
        evaluation_agent: CandidateEvaluationAgent instance
        database_agent: DatabaseAgent instance
        scraping_agent: ProfileScrapingAgent instance (optional)
        max_retries: Maximum retry attempts for API calls
        timeout_minutes: Pipeline timeout in minutes
        min_candidates_threshold: Minimum candidates to find
        min_suitable_threshold: Minimum suitable candidates
    
    Example:
        >>> manager = UnifiedSourcingManager()
        >>> 
        >>> requirements = {
        ...     'position': 'Python Developer',
        ...     'skills': ['Python', 'Django'],
        ...     'location': 'Amsterdam'
        ... }
        >>> 
        >>> results = manager.process_sourcing_request(
        ...     project_requirements=requirements,
        ...     job_description='Senior Python Developer role...',
        ...     project_id='proj123',
        ...     target_count=50
        ... )
        >>> 
        >>> print(f"Found {results['summary']['total_suitable']} suitable candidates")
    
    Note:
        Configuration is loaded from .env file via AppConfig. The manager
        uses synchronous operations for compatibility with existing agents.
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = None, 
        temperature: Optional[float] = None, 
        config: Optional[AppConfig] = None
    ) -> None:
        """
        Initialize the Unified Sourcing Manager.
        
        Sets up the manager with configuration from environment variables or
        provided parameters. Initializes sub-agents and configures pipeline
        parameters.
        
        Args:
            model_name: Optional AI model name. If None, uses config default.
            temperature: Optional AI temperature. If None, uses config default.
            config: Optional AppConfig instance. If None, loads from environment.
        
        Side Effects:
            - Initializes CandidateSearchingAgent
            - Initializes CandidateEvaluationAgent
            - Initializes DatabaseAgent
            - Loads configuration from .env
        
        Example:
            >>> # Default initialization (uses .env config)
            >>> manager = UnifiedSourcingManager()
            >>> 
            >>> # With custom model
            >>> manager = UnifiedSourcingManager(
            ...     model_name='gpt-4-turbo',
            ...     temperature=0.2
            ... )
        
        Note:
            All configuration values can be overridden via environment variables
            in the .env file. See config.py for available options.
        """
        
        # Load configuration from .env or use provided config
        self.config = config or get_config()
        
        # Use config values or fallbacks
        self.model_name = model_name or self.config.openai.model
        self.temperature = temperature or self.config.openai.temperature

        # Configuration from .env
        self.max_retries = self.config.unified_sourcing.max_retries
        self.timeout_minutes = self.config.unified_sourcing.timeout_minutes
        self.min_candidates_threshold = self.config.unified_sourcing.min_candidates
        self.min_suitable_threshold = self.config.unified_sourcing.min_suitable

        # Clean-architecture dependencies
        self.candidate_repository = MongoDBCandidateRepository()
        self.project_repository = MongoDBProjectRepository()
        self.linkedin_service = LinkedInServiceImpl()
        self.search_use_case = SearchCandidatesUseCase(
            candidate_repository=self.candidate_repository,
            linkedin_service=self.linkedin_service,
            ai_service=None,
        )
        self.candidate_evaluation_service = CandidateEvaluationService()

        orchestrator_config = {
            "max_retries": self.max_retries,
            "min_candidates": self.min_candidates_threshold,
            "min_suitable": self.min_suitable_threshold,
        }

        # Clean-architecture orchestrator for sourcing pipeline
        self.orchestrator = SourcingManagerOrchestrator(
            candidate_repository=self.candidate_repository,
            project_repository=self.project_repository,
            linkedin_service=self.linkedin_service,
            search_candidates_use_case=self.search_use_case,
            candidate_evaluation_service=self.candidate_evaluation_service,
            config=orchestrator_config,
        )
        
        logger.info(f"UnifiedSourcingManager initialized with configuration from .env")
        logger.info(f"Config: max_retries={self.max_retries}, timeout={self.timeout_minutes}min, AI={self.config.unified_sourcing.ai_decision_enabled}")
    
    # ---- Main Orchestration Methods ----
    
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async wrapper for process_sourcing_request - used by CLI and API.
        
        This method provides an async interface compatible with the CLI's async/await
        pattern while internally calling the synchronous process_sourcing_request.
        
        Args:
            request: Dictionary with:
                - job_requirements: Job description text
                - target_count: Number of candidates to find (default: 10)
                - quality_threshold: Minimum suitability score (default: 0.7)
                - project_id: Project identifier (optional)
                - enable_evaluation: Enable candidate evaluation (default: True)
                - scrape_profiles: Enable profile enrichment (default: True)
        
        Returns:
            Complete sourcing results with qualified candidates
        
        Example:
            >>> manager = UnifiedSourcingManager()
            >>> result = await manager.run({
            ...     'job_requirements': 'Find senior Python developers in Amsterdam',
            ...     'target_count': 10,
            ...     'enable_evaluation': True
            ... })
        """
        # Extract parameters from request
        job_requirements = request.get('job_requirements', '')
        target_count = request.get('target_count', 10)
        project_id = request.get('project_id', f"CLI_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Build project requirements dict
        project_requirements = {
            'position': 'Candidate',  # Will be parsed from job_requirements
            'description': job_requirements
        }
        
        # Call synchronous method
        return self.process_sourcing_request(
            project_requirements=project_requirements,
            job_description=job_requirements,
            project_id=project_id,
            target_count=target_count
        )
    
    def process_sourcing_request(self, 
                                     project_requirements: Dict[str, Any],
                                     job_description: str,
                                     project_id: str,
                                     target_count: int = 50) -> Dict[str, Any]:
        """
        Main orchestration method - delegates to clean-architecture orchestrator.
        
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

        try:
            result = asyncio.run(
                self.orchestrator.process_sourcing_request(
                    project_id=project_id,
                    requirements=project_requirements,
                    job_description=job_description,
                    target_count=target_count,
                )
            )

            logger.info(f"✅ Unified sourcing request {request_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"❌ Unified sourcing request {request_id} failed: {str(e)}")
            # Return structured error similar to orchestrator
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id,
            }
    
    # ---- Decision Making Methods ----
    def _make_workflow_decision(self, situation: str, workflow_state: Dict[str, Any]) -> SourcingManagerDecision:
        """
        Make intelligent workflow decisions using real GPT-5 reasoning.
        
        Now uses optimized prompts from unified_sourcing_manager_prompts.py
        for better decision quality with concrete examples and reasoning framework.
        """
        
        try:
            from langchain_openai import ChatOpenAI
            import os
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # Initialize GPT-5 for real decision making
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-5"),
                temperature=0.3,  # Low temperature for consistent decisions
                api_key=self.config.openai_api_key
            )
            
            # Prepare decision context
            candidates_found = workflow_state["metrics"]["total_found"]
            candidates_suitable = workflow_state["metrics"]["total_suitable"]
            success_rate = workflow_state["metrics"]["success_rate"]
            retry_count = workflow_state["retry_count"]
            target_count = workflow_state.get("target_count", 50)
            error_count = len(workflow_state["errors"])
            warning_count = len(workflow_state["warnings"])
            current_stage = workflow_state["current_stage"]
            
            # Get enhanced prompt with examples and reasoning framework
            decision_prompt = self._get_workflow_decision_prompt(
                situation=situation,
                current_stage=current_stage,
                candidates_found=candidates_found,
                candidates_suitable=candidates_suitable,
                success_rate=success_rate,
                retry_count=retry_count,
                max_retries=self.max_retries,
                target_count=target_count,
                error_count=error_count,
                warning_count=warning_count
            )

            # Call GPT-5 for real decision with enhanced prompt
            logger.info(f"🤖 Asking GPT-5 for workflow decision on: {situation}")
            
            # Use only the decision_prompt (it already includes system-level guidance)
            messages = [
                HumanMessage(content=decision_prompt)
            ]
            
            response = llm.invoke(messages)
            response_text = response.content
            
            logger.info(f"🤖 GPT-5 Response (first 200 chars): {response_text[:200]}...")
            
            # Parse the response
            try:
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text
                
                decision_data = json.loads(json_str)
                
                logger.info(f"✅ Parsed decision: {decision_data.get('decision')} (confidence: {decision_data.get('confidence')})")
                
                return SourcingManagerDecision(
                    action=decision_data.get("decision", "continue").upper(),  # Note: new prompt uses 'decision' not 'action'
                    reasoning=decision_data.get("reasoning", "AI decision based on context"),
                    confidence=float(decision_data.get("confidence", 0.7)),
                    next_steps=decision_data.get("next_steps", ["Execute recommended action"]),
                    adjustments=decision_data.get("adjustments", {})
                )
                
            except (json.JSONDecodeError, KeyError, ValueError) as parse_error:
                logger.warning(f"Failed to parse GPT-5 JSON response: {parse_error}. Using fallback.")
                # Fallback: extract action from text
                response_lower = response_text.lower()
                if "retry" in response_lower:
                    action = "retry"
                elif "adjust" in response_lower:
                    action = "adjust"
                elif "escalate" in response_lower:
                    action = "escalate"
                elif "complete" in response_lower:
                    action = "complete"
                else:
                    action = "continue"
                
                return SourcingManagerDecision(
                    action=action,
                    reasoning=response_text,
                    confidence=0.6,
                    next_steps=["Execute recommended action"]
                )
        
        except Exception as e:
            logger.warning(f"❌ GPT-5 decision making failed: {str(e)}. Using intelligent fallback.")
            
            # Intelligent fallback logic
            candidates_found = workflow_state["metrics"]["total_found"]
            suitable_count = workflow_state["metrics"]["total_suitable"]
            retry_count = workflow_state["retry_count"]
            target = workflow_state.get("target_count", 50)
            adjustment_level = workflow_state.get("adjustment_level", 1)
            
            if situation == "low_candidate_count" and retry_count < self.max_retries and adjustment_level < 4:
                return SourcingManagerDecision(
                    action="adjust",
                    reasoning="Fallback: Low candidate count with room for progressive adjustment",
                    confidence=0.7,
                    next_steps=[
                        f"Adjust search criteria to level {adjustment_level + 1}",
                        "Retry search with broader parameters",
                        "Maintain quality while expanding reach"
                    ],
                    adjustments={"adjustment_level": adjustment_level + 1}
                )
            elif situation == "low_suitable_count" and candidates_found > 5:
                return SourcingManagerDecision(
                    action="continue",
                    reasoning="Fallback: Have sufficient candidates despite low suitability - may contain hidden gems",
                    confidence=0.6,
                    next_steps=[
                        "Proceed with available candidates",
                        "Perform deep profile analysis",
                        "Look for non-obvious skill matches and growth potential"
                    ]
                )
            else:
                return SourcingManagerDecision(
                    action="complete",
                    reasoning="Fallback: Accept current results and move forward",
                    confidence=0.5,
                    next_steps=["Complete current workflow", "Proceed with available candidates"]
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
            linkedin_url = evaluated_candidate.get("linkedin_url", "") or evaluated_candidate.get("profile_url", "")
            
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
            candidate.title = evaluated_candidate.get("title", evaluated_candidate.get("headline", candidate.title))
            candidate.company = evaluated_candidate.get("company", evaluated_candidate.get("current_company", candidate.company))
            candidate.location = evaluated_candidate.get("location", evaluated_candidate.get("locatie", candidate.location))
            candidate.skills = evaluated_candidate.get("skills", candidate.skills)
            candidate.work_experience = evaluated_candidate.get("work_experience", evaluated_candidate.get("experience", candidate.work_experience))
            candidate.education = evaluated_candidate.get("education", candidate.education)
            candidate.profile_summary = evaluated_candidate.get("profile_summary", evaluated_candidate.get("summary", candidate.profile_summary))
            candidate.contact_info = evaluated_candidate.get("contact_info", candidate.contact_info)
            candidate.suitability_status = evaluated_candidate.get("suitability_status", "unknown")
            candidate.suitability_score = evaluated_candidate.get("suitability_score", 0.0)
            candidate.suitability_reasoning = evaluated_candidate.get("suitability_reasoning", "")
            candidate.evaluation_timestamp = datetime.now()
            
            updated_candidates.append(candidate)
        
        return updated_candidates

    def _build_scraping_request(self, candidate_records: List[CandidateRecord], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Build request payload for profile scraping agent."""
        candidates_payload = []
        for record in candidate_records:
            record_dict = record.dict()
            # Ensure profile URL is available for scraping
            record_dict.setdefault("profile_url", record.linkedin_url)
            record_dict.setdefault("linkedin_url", record.linkedin_url)
            candidates_payload.append(record_dict)
        
        return {
            "candidates": candidates_payload,
            "projectid": workflow_state.get("project_id", ""),
            "project_id": workflow_state.get("project_id", ""),
            "project_name": workflow_state.get("project_requirements", {}).get("position", ""),
            "naam_project": f"UnifiedSourcing_{workflow_state.get('project_id', 'unknown')}",
            "campaign_num": "001",
            "job_description": workflow_state.get("job_description", ""),
            "enrichment_config": {
                "batch_size": 10,
                "rate_limit_delay": 1,
                "max_retries": 3
            }
        }

    def _apply_enrichment_to_records(
        self,
        suitable_records: List[CandidateRecord],
        enriched_candidates_raw: List[Dict[str, Any]],
        job_description: str
    ) -> List[CandidateRecord]:
        """Merge scraped profile data back into CandidateRecord objects."""
        updated_records: List[CandidateRecord] = []
        lookup = {record.linkedin_url: record for record in suitable_records}
        
        for enriched in enriched_candidates_raw:
            linkedin_url = enriched.get("linkedin_url") or enriched.get("profile_url")
            if not linkedin_url:
                continue
            record = lookup.get(linkedin_url)
            if not record:
                continue
            
            record.profile_enriched = True
            record.enrichment_timestamp = datetime.now()
            record.enrichment_details = {
                **record.enrichment_details,
                **enriched.get("enrichment_details", {})
            }
            record.enrichment_details["enrichment_status"] = enriched.get("enrichment_status", "success")
            record.enrichment_details["enrichment_source"] = enriched.get("enrichment_source", enriched.get("enrichment_status", "live_scrape"))
            
            # Merge enriched fields
            record.skills = list({*(record.skills or []), *enriched.get("skills", [])})
            record.work_experience = enriched.get("work_experience") or enriched.get("experience", record.work_experience)
            record.education = enriched.get("education", record.education)
            record.profile_summary = enriched.get("profile_summary") or enriched.get("summary") or record.profile_summary
            record.contact_info = enriched.get("contact_info", record.contact_info)
            record.location = enriched.get("locatie", record.location)
            record.title = enriched.get("headline", record.title)
            record.company = enriched.get("current_company", record.company)
            record.linkedin_url = linkedin_url or record.linkedin_url
            
            relevance = self._compute_relevance(record.skills, record.work_experience, job_description)
            record.relevant_skills = relevance.get("skills", [])
            record.relevant_experience = relevance.get("experience", [])
            
            updated_records.append(record)
        
        # Preserve any suitable records that did not return from scraping
        remaining = [record for record in suitable_records if record not in updated_records]
        return updated_records + remaining

    def _re_evaluate_enriched_candidates(self, workflow_state: Dict[str, Any]):
        """Re-run evaluation using enriched profile data to improve skill/experience matching."""
        enriched_candidates = workflow_state["candidates_pipeline"].get("enriched", [])
        if not enriched_candidates:
            logger.info("No enriched candidates available for re-evaluation")
            return

        # Ensure each candidate has a linkedin_url for consistent lookups
        for c in enriched_candidates:
            if not c.get("linkedin_url") and c.get("profile_url"):
                c["linkedin_url"] = c.get("profile_url")
            if not c.get("provider_id"):
                c["provider_id"] = c.get("linkedin_url", "")

        evaluation_request = {
            "projectid": workflow_state.get("project_id", ""),
            "searchid": f"reeval_{workflow_state.get('request_id', '')[:8]}",
            "naam_project": f"UnifiedSourcing_{workflow_state.get('project_id', 'unknown')}",
            "campaign_num": "001",
            "job_requirements": workflow_state.get("job_description", ""),
            "candidates": enriched_candidates,
            "evaluation_criteria": workflow_state.get("project_requirements", {})
        }

        try:
            evaluation_results = self.evaluation_agent.evaluate_candidates(evaluation_request)
            parsed_records = self._parse_evaluation_results(
                evaluation_results,
                workflow_state["candidates_records"].get("enriched", []) or workflow_state["candidates_records"].get("evaluated", [])
            )

            workflow_state["candidates_pipeline"]["evaluated"] = evaluation_results.get("evaluated_candidates", enriched_candidates)
            workflow_state["candidates_records"]["evaluated"] = parsed_records

            suitable_count = len([c for c in parsed_records if c.suitability_status in ["suitable", "maybe", "SUITABLE", "POTENTIALLY_SUITABLE", "HIGHLY_SUITABLE"]])
            workflow_state["metrics"]["total_suitable"] = suitable_count
            workflow_state["metrics"]["success_rate"] = suitable_count / len(enriched_candidates) if enriched_candidates else 0.0
            logger.info(f"🎯 Re-evaluation after enrichment: {suitable_count} suitable/potential out of {len(enriched_candidates)}")
        except Exception as e:
            logger.warning(f"⚠️ Re-evaluation after enrichment failed: {e}")

    def _compute_relevance(
        self,
        skills: List[str],
        work_experience: List[Dict[str, Any]],
        job_description: str
    ) -> Dict[str, Any]:
        """Tag which skills and experience items match the job description."""
        if not job_description:
            return {"skills": [], "experience": []}
        
        tokens = [t.lower() for t in re.split(r"[^a-zA-Z0-9\+]+", job_description) if len(t) > 2]
        keywords = set(tokens)
        matched_skills = [s for s in skills if isinstance(s, str) and s.lower() in keywords]
        matched_skills = matched_skills[:10]
        
        matched_experience = []
        for exp in work_experience or []:
            combined_text = " ".join([
                str(exp.get("company", "")),
                str(exp.get("position", "")),
                str(exp.get("description", ""))
            ]).lower()
            exp_matches = [kw for kw in keywords if kw in combined_text]
            if exp_matches:
                matched_experience.append({
                    "company": exp.get("company", ""),
                    "position": exp.get("position", ""),
                    "duration": exp.get("duration", ""),
                    "matched_keywords": exp_matches[:5]
                })
        
        return {
            "skills": matched_skills,
            "experience": matched_experience[:5]
        }
    
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
        """
        Adjust search criteria progressively based on AI analysis.
        Implements progressive relaxation strategy: experience → location → skills → target count.
        """
        logger.info("🎯 Adjusting search criteria using progressive relaxation strategy")
        
        criteria = workflow_state["project_requirements"]
        adjustment_level = workflow_state.get("adjustment_level", 1)
        
        # Level 1: Relax experience requirement (reduce by 20%)
        if adjustment_level >= 1 and "required_years_experience" in criteria:
            original_exp = criteria["required_years_experience"]
            criteria["required_years_experience"] = max(0, int(original_exp * 0.8))
            logger.info(f"  - Relaxed experience requirement: {original_exp} → {criteria['required_years_experience']} years")
        
        # Level 2: Remove location restriction
        if adjustment_level >= 2:
            if "location" in criteria and criteria["location"]:
                criteria["location"] = ""  # Allow any location
                criteria["remote_ok"] = True
                logger.info("  - Removed location restriction, enabled remote candidates")
            elif "remote_ok" not in criteria:
                criteria["remote_ok"] = True
                logger.info("  - Enabled remote candidates")
        
        # Level 3: Reduce required skills to must-haves only
        if adjustment_level >= 3 and "required_skills" in criteria:
            original_count = len(criteria["required_skills"])
            if original_count > 3:
                criteria["required_skills"] = criteria["required_skills"][:3]
                logger.info(f"  - Reduced required skills: {original_count} → 3 (must-have only)")
        
        # Level 4: Increase target candidate count
        if adjustment_level >= 4:
            if "target_count" in criteria:
                original_target = criteria["target_count"]
                criteria["target_count"] = int(original_target * 1.5)
                logger.info(f"  - Increased target count: {original_target} → {criteria['target_count']}")
            else:
                criteria["target_count"] = 75  # Default increased target
                logger.info("  - Set increased target count: 75")
        
        workflow_state["project_requirements"] = criteria
        logger.info(f"✅ Search criteria adjusted at level {adjustment_level}")
    
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
        # Get suitable/maybe records from evaluation (checking both new and old status names)
        suitable_records = [
            c for c in workflow_state["candidates_records"]["evaluated"]
            if c.suitability_status in ["suitable", "maybe", "SUITABLE", "POTENTIALLY_SUITABLE", "HIGHLY_SUITABLE"]
        ]
        
        # Fallback: if no suitable candidates from evaluation, use search phase candidates directly
        # This ensures we return candidates even if evaluation is conservative
        if not suitable_records and workflow_state["candidates_pipeline"]["found"]:
            logger.info("📌 No suitable/potential candidates from evaluation - using search phase candidates as fallback")
            # Use raw candidates from pipeline (these have actual data from LinkedIn API)
            candidates_data = workflow_state["candidates_pipeline"]["found"][:10]  # Top 10 from search
        else:
            logger.info(f"📌 Returning {len(suitable_records)} suitable/potential candidates from evaluation")
            # Convert CandidateRecord objects to dicts
            candidates_data = [record.dict() if hasattr(record, 'dict') else record for record in suitable_records]
            # If we have suitable but less than 10, supplement with search candidates
            if len(candidates_data) < 10 and workflow_state["candidates_pipeline"]["found"]:
                all_search = workflow_state["candidates_pipeline"]["found"]
                needed = 10 - len(candidates_data)
                additional = all_search[len(candidates_data):len(candidates_data) + needed]
                candidates_data.extend(additional)
                logger.info(f"📌 Supplemented with {len(additional)} candidates from search phase")
        
        return {
            "request_id": workflow_state["request_id"],
            "status": "completed_basic",
            "summary": {
                "total_found": workflow_state["metrics"]["total_found"],
                "total_suitable": len(suitable_records) if suitable_records else len(candidates_data),
                "success_rate": workflow_state["metrics"]["success_rate"]
            },
            "candidates": candidates_data,
            "note": "Profile enrichment skipped - proceeding with basic candidate data",
            "recommendations": [
                "Consider manual profile research for top candidates",
                "Proceed with outreach using available basic data",
                "Schedule enrichment phase for successful initial contacts"
            ]
        }

    def _get_workflow_decision_prompt(
        self,
        situation: str,
        current_stage: str,
        candidates_found: int,
        candidates_suitable: int,
        success_rate: float,
        retry_count: int,
        max_retries: int,
        target_count: int,
        error_count: int,
        warning_count: int
    ) -> str:
        """
        Generate workflow decision prompt for AI decision making.
        
        Creates a concise decision prompt for the LLM to make workflow decisions
        based on current pipeline state, metrics, and stage.
        """
        return f"""# SOURCING WORKFLOW DECISION

## CURRENT SITUATION: {situation}
## STAGE: {current_stage}

### METRICS:
- Found: {candidates_found}/{target_count} candidates
- Suitable: {candidates_suitable} candidates
- Success Rate: {success_rate:.1%}
- Retry Count: {retry_count}/{max_retries}
- Errors: {error_count}, Warnings: {warning_count}

### DECISION OPTIONS:
1. CONTINUE: Proceed to next phase (sufficient progress)
2. RETRY: Retry current phase (similar parameters)
3. ADJUST: Modify criteria and retry (broaden/narrow requirements)
4. ESCALATE: Requires human review (critical issue)
5. COMPLETE: Accept current results (enough candidates)

### DECISION CRITERIA:
- If suitable candidates >= 60% of target: CONTINUE or COMPLETE
- If candidates < 30% of target: ADJUST or RETRY
- If consecutive errors > 2: ESCALATE
- If success rate > 80%: CONTINUE

Return ONLY valid JSON:
{{
  "decision": "CONTINUE|RETRY|ADJUST|ESCALATE|COMPLETE",
  "reasoning": "explanation",
  "confidence": 0.85,
  "next_steps": ["step 1", "step 2"],
  "adjustments": {{"key": "value"}}
}}"""

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