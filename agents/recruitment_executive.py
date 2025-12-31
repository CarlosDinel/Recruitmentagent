"""
Recruitment Executive Agent - Central Orchestrator

This module implements the RecruitmentExecutiveAgent, the central orchestrator for the
entire recruitment workflow. It follows the Orchestrator pattern, coordinating specialized
manager agents to deliver end-to-end recruitment automation.

Architecture:
============

The agent implements a hierarchical delegation pattern:

    User Request / LinkedIn Webhook
            │
            ▼
    ┌───────────────────────┐
    │ RecruitmentExecutive   │  ← This Agent (Orchestrator)
    │      Agent             │
    └───────────┬─────────────┘
                │
        ┌───────┼───────┐
        │       │       │
        ▼       ▼       ▼
    ┌──────┐ ┌──────┐ ┌──────┐
    │Source│ │Outreach│ │Database│
    │Manager│ │Manager │ │ Agent  │
    └──────┘ └──────┘ └──────┘

Design Patterns:
===============

1. **Orchestrator Pattern**: Coordinates without implementing details
2. **Dependency Injection**: Managers injected via lazy initialization
3. **State Machine**: TypedDict-based state management with LangGraph
4. **Strategy Pattern**: Different recruitment strategies (fast_track, bulk_hiring, etc.)
5. **Template Method**: Workflow nodes define algorithm skeleton

Workflow Stages:
===============

1. **Request Processing**: Identify source, extract data, validate
2. **Analysis**: Parse requirements, assess needs
3. **Project Management**: Create/update projects via DatabaseAgent
4. **Sourcing**: Delegate to UnifiedSourcingManager
5. **Outreach**: Delegate to OutreachManager
6. **Monitoring**: Track progress, calculate metrics
7. **Reporting**: Generate comprehensive reports

State Management:
================

Uses TypedDict for type-safe state management. State flows through workflow nodes,
each node updating relevant fields and passing control to the next based on
conditional routing logic.

Example Usage:
==============

    from agents.recruitment_executive import RecruitmentExecutiveAgent
    
    # Initialize agent
    agent = RecruitmentExecutiveAgent()
    
    # Process a user request
    result = await agent.execute({
        'request': 'Find a senior Python developer with 5+ years experience'
    })
    
    # Access results
    if result['success']:
        processing_result = result['result']['processing_result']
        parsed_reqs = result['result']['parsed_requirements']

Error Handling:
==============

- Graceful degradation: If managers unavailable, uses fallback strategies
- Comprehensive logging: All operations logged with appropriate levels
- Validation: Input validated before processing
- Exception handling: Errors caught and returned in structured format

Dependencies:
=============

- UnifiedSourcingManager: For candidate discovery
- OutreachManager: For candidate engagement
- DatabaseAgent: For data persistence (monopoly pattern)
"""

# ---- Package imports ----
from typing import List, Dict, Any, Optional, Sequence, Annotated
from datetime import datetime
import json
import logging
import os
import sys

# LangGraph and LangChain for agent framework
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.graph.message import add_messages
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

# Environment and configuration
from dotenv import load_dotenv
load_dotenv()

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Clean Architecture imports - REFACTORED
from agents.infrastructure.services import (
    LLMService,
    DatabaseService,
    ConfigService
)
from agents.shared.logging_config import get_logger
from agents.shared.error_handling import DatabaseError, LLMError, ValidationError

# Import use cases
from agents.application.usecases.process_recruitment_request import ProcessRecruitmentRequestUseCase
from agents.application.usecases.execute_sourcing_workflow import ExecuteSourcingWorkflowUseCase
from agents.application.usecases.execute_outreach_campaign import ExecuteOutreachCampaignUseCase
from agents.application.usecases.monitor_progress import MonitorProgressUseCase
from agents.application.usecases.generate_report import GenerateReportUseCase

# Import your tools and other agents
from tools.get_projects import get_all_projects, convert_project_to_json

# NOTE: Circular import prevention - Import flows only when needed
# from flows.recruitment_executive_flow import RecruitmentExecutiveFlow

# ============================================================================
# EMBEDDED PROMPTS - Recruitment Executive Agent
# ============================================================================

class RecruitmentPrompts:
    """
    Embedded prompts for the RecruitmentExecutiveAgent.
    
    These prompts guide the agent in breaking down user requests into tasks,
    coordinating sub-agents, and ensuring accurate recruitment outcomes.
    """

    @staticmethod
    def user_request_prompt(user_request: str) -> str:
        """System prompt to analyze user requests and orchestrate the recruitment process using the STAR methodology."""
        return f"""# RECRUITMENT EXECUTIVE ORCHESTRATOR

## USER REQUEST
{user_request}

## YOUR ROLE
You are the Executive Recruitment Orchestrator, responsible for breaking down recruitment requests into atomic, actionable tasks and coordinating specialized sub-agents to deliver complete recruitment outcomes.

## CORE METHODOLOGY: STAR LOOP

### S – SOLICIT (Clarify & Validate)
- **ANALYZE** the user request for completeness and specificity
- **IDENTIFY** missing critical information (job requirements, timeline, budget, candidate profile)
- **ASK** targeted clarifying questions if the request is underspecified
- **VALIDATE** that you have sufficient details to proceed

### T – TASKIFY (Break Down & Structure)
- **DECOMPOSE** the request into minimum viable atomic subtasks
- **PRIORITIZE** tasks by dependency and urgency
- **FORMAT** as numbered markdown list with clear deliverables
- **ENSURE** each task has measurable success criteria

### A – ASSIGN (Delegate & Execute)
- **ROUTE** each subtask to the appropriate Manager Agent with explicit inputs
- **PROVIDE** complete context and required parameters
- **SET** clear expectations and deadlines
- **TRACK** delegation status and agent availability

### R – REVIEW (Validate & Consolidate)
- **EVALUATE** outputs from sub-agents for completeness and quality
- **IDENTIFY** gaps, errors, or incomplete deliverables
- **REASSIGN** failed tasks with refined instructions
- **CONSOLIDATE** results into structured summary for user

## CRITICAL GUARDRAILS
-  LinkedIn Authentication Protocol: Run LinkedIn-auth-check at workflow start
-  Database Integrity Rules: NEVER write directly to Database Agent
-  Task Decomposition Standards: ONE atomic task per sub-agent call

## RESPONSE STRUCTURE
1. REQUEST ANALYSIS: Summary of understood requirements
2. TASK BREAKDOWN: Numbered list with specific deliverables
3. EXECUTION PLAN: Task dependencies and sequencing
4. SUCCESS METRICS: Key performance indicators

Now process the user request following this framework."""

    @staticmethod
    def parse_requirements_prompt(user_request: str) -> str:
        """Prompt for parsing and extracting requirements from user requests."""
        return f"""# REQUIREMENT EXTRACTION SPECIALIST

Extract and structure ALL relevant recruitment requirements from this request:

{user_request}

Return ONLY valid JSON with this structure:
{{
  "position": "job title",
  "skills": ["skill1", "skill2"],
  "location": "location or empty",
  "experience_level": "Junior|Mid-level|Senior|Lead|Executive",
  "urgency": "urgent|normal|low",
  "quantity": 1,
  "work_type": "Full-time|Part-time|Contract|Freelance",
  "remote_preference": "Remote|Hybrid|On-site",
  "raw_request": "{user_request}"
}}

CRITICAL: Return ONLY valid JSON, no additional text."""

    @staticmethod
    def plan_strategy_prompt(user_request: str, parsed_requirements: dict, current_projects: list) -> str:
        """Prompt for planning recruitment strategy based on available projects and requirements."""
        return f"""# RECRUITMENT STRATEGY PLANNER

## CONTEXT
User Request: {user_request}
Requirements: {parsed_requirements}
Projects: {current_projects}

Analyze and design optimal recruitment strategy.

Return ONLY valid JSON:
{{
  "recruitment_strategy": "fast_track|standard_recruitment|bulk_hiring|specialized_search|executive_search",
  "next_action": "sourcing|outreach|monitor|complete",
  "reasoning": ["reason1", "reason2"],
  "priority_level": "high|medium|low",
  "estimated_timeline": "X weeks"
}}"""

    @staticmethod
    def generate_report_prompt(campaign_data: dict, pipeline_metrics: dict, performance_data: dict) -> str:
        """Prompt for generating a comprehensive recruitment report."""
        return f"""# RECRUITMENT CAMPAIGN ANALYST

Generate comprehensive recruitment campaign report.

Campaign Data: {campaign_data}
Pipeline Metrics: {pipeline_metrics}
Performance Data: {performance_data}

Return ONLY valid JSON:
{{
  "report_id": "recruitment_report_YYYYMMDD",
  "executive_summary": {{
    "campaign_status": "successful|in_progress|needs_attention|failed",
    "overall_grade": "A|B|C|D|F"
  }},
  "recommendations": {{
    "immediate_actions": ["action1", "action2"],
    "process_improvements": ["improvement1"]
  }}
}}"""

    @staticmethod
    def monitor_progress_prompt(pipeline_data: dict, sourcing_status: dict, outreach_status: dict) -> str:
        """Prompt for monitoring and assessing recruitment campaign progress."""
        return f"""# RECRUITMENT PROGRESS MONITOR

Assess current campaign progress and determine if intervention is needed.

Pipeline: {pipeline_data}
Sourcing: {sourcing_status}
Outreach: {outreach_status}

Return ONLY valid JSON:
{{
  "monitoring_summary": {{
    "overall_health": "excellent|good|fair|poor",
    "intervention_needed": true,
    "urgency_level": "critical|high|medium|low"
  }},
  "immediate_actions": ["action1"],
  "success_predictions": {{
    "probability_of_success": "XX%",
    "estimated_completion": "X weeks"
  }}
}}"""

# agents imports (legacy - kept for backward compatibility)
try:
    from agents.sourcing_manager_unified import UnifiedSourcingManager
except ImportError:
    UnifiedSourcingManager = None

try:
    from agents.database_agent import DatabaseAgent
except ImportError:
    DatabaseAgent = None

try:
    from agents.outreach_manager import OutreachManager
except ImportError:
    OutreachManager = None

# Logging - refactored to use centralized logger
logger = get_logger('RecruitmentExecutiveAgent')

# ============================================================================
# CONFIGURATION - REFACTORED
# ============================================================================

def get_ai_config() -> Dict[str, Any]:
    """
    Get AI model configuration from environment variables.
    
    REFACTORED: Now uses ConfigService instead of direct os.getenv() calls.
    Kept for backward compatibility with existing code.
    
    Returns:
        Dict containing AI configuration from ConfigService
    
    Example:
        >>> config = get_ai_config()
        >>> print(config['model'])
        'gpt-5'
    """
    config_service = ConfigService.get_instance()
    return config_service.get_llm_config()

# ============================================================================
# STATE DEFINITIONS
# ============================================================================

class RecruitmentExecutiveState(TypedDict):
    """
    State object for the Recruitment Executive Agent workflow.
    
    This TypedDict defines the complete state structure that flows through
    the recruitment workflow. Each workflow node can read and update
    relevant fields, ensuring type safety and clear state management.
    
    Attributes:
        messages: Sequence of LangChain messages (HumanMessage, AIMessage, etc.)
        user_request: Original user request string
        current_projects: List of active recruitment projects
        active_campaigns: List of ongoing outreach campaigns
        candidate_pipeline: Dictionary mapping pipeline stages to candidate lists
            Keys: 'sourced', 'contacted', 'responded', 'interviewed', 'hired'
        recruitment_strategy: Current strategy ('fast_track', 'bulk_hiring', etc.)
        next_action: Next workflow action to execute
        reasoning: List of reasoning steps for transparency
        human_review_required: Flag indicating if human intervention needed
        current_stage: Current workflow stage identifier
        processing_result: Results from request processing
        parsed_requirements: Structured requirements extracted from user request
        project_creation_result: Results from project creation attempt
    
    Example:
        >>> state: RecruitmentExecutiveState = {
        ...     'messages': [HumanMessage(content='Find Python dev')],
        ...     'user_request': 'Find Python dev',
        ...     'current_projects': [],
        ...     'active_campaigns': [],
        ...     'candidate_pipeline': {'sourced': [], 'contacted': []},
        ...     'recruitment_strategy': 'standard_recruitment',
        ...     'next_action': 'sourcing',
        ...     'reasoning': None,
        ...     'human_review_required': False,
        ...     'current_stage': 'request_processed',
        ...     'processing_result': None,
        ...     'parsed_requirements': None,
        ...     'project_creation_result': None
        ... }
    
    Note:
        All fields are optional except those required by LangGraph's MessagesState.
        The TypedDict ensures type checking at development time.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_request: str
    current_projects: List[Dict[str, Any]]
    active_campaigns: List[Dict[str, Any]]
    candidate_pipeline: Dict[str, List[Dict[str, Any]]]
    recruitment_strategy: str
    next_action: str
    reasoning: Optional[List[str]]
    human_review_required: Optional[bool]
    current_stage: Optional[str]
    processing_result: Optional[Dict[str, Any]]
    parsed_requirements: Optional[Dict[str, Any]]
    project_creation_result: Optional[Dict[str, Any]]


# ============================================================================
# CONSTANTS
# ============================================================================

EXAMPLE_USER_REQUEST: str = (
    "Find and recruit a senior data scientist with expertise in "
    "machine learning and Python for our Amsterdam office."
)
"""Example user request for documentation and testing purposes."""


# ============================================================================
# MAIN AGENT CLASS
# ============================================================================

class RecruitmentExecutiveAgent:
    """
    Central orchestrator for the recruitment workflow.
    
    The RecruitmentExecutiveAgent coordinates the entire recruitment process,
    from initial request processing through candidate sourcing, outreach,
    and final reporting. It delegates specialized tasks to manager agents
    while maintaining overall workflow state and routing logic.
    
    Responsibilities:
        - Process user requests and LinkedIn API webhooks
        - Parse and validate recruitment requirements
        - Coordinate with SourcingManager for candidate discovery
        - Coordinate with OutreachManager for candidate engagement
        - Manage candidate pipeline state
        - Generate comprehensive recruitment reports
        - Handle error recovery and graceful degradation
    
    Design:
        - Uses dependency injection for manager agents
        - Implements lazy initialization to avoid circular imports
        - Follows the Orchestrator pattern (coordinates, doesn't implement)
        - State-based workflow with LangGraph integration
    
    Attributes:
        state: Current workflow state (RecruitmentExecutiveState)
        config: AI model configuration dictionary
        logger: Logger instance for this agent
        sourcing_manager: UnifiedSourcingManager instance (lazy loaded)
        database_agent: DatabaseAgent instance (lazy loaded)
        outreach_manager: OutreachManager instance (lazy loaded)
    
    Example:
        >>> # Initialize agent
        >>> agent = RecruitmentExecutiveAgent()
        >>> 
        >>> # Process a recruitment request
        >>> result = await agent.execute({
        ...     'request': 'Find a senior Python developer'
        ... })
        >>> 
        >>> # Check results
        >>> if result['success']:
        ...     print(f"Stage: {result['stage']}")
        ...     print(f"Result: {result['result']['processing_result']}")
    
    Note:
        Manager agents are initialized lazily to avoid circular import issues.
        If a manager fails to initialize, the agent continues with reduced
        functionality (graceful degradation).
    """

    def __init__(
        self, 
        state: Optional[RecruitmentExecutiveState] = None, 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the Recruitment Executive Agent.
        
        REFACTORED: Now uses centralized services (LLMService, DatabaseService, ConfigService)
        instead of direct initialization. Backward compatible with old API.
        
        Args:
            state: Optional initial state. If None, creates default empty state.
            config: Optional AI configuration. If None, loads from ConfigService.
        
        Example:
            >>> agent = RecruitmentExecutiveAgent()
            >>> agent = RecruitmentExecutiveAgent(state=custom_state)
        """
        # Initialize state (unchanged)
        self.state = state or {
            'messages': [],
            'user_request': '',
            'current_projects': [],
            'active_campaigns': [],
            'candidate_pipeline': {},
            'recruitment_strategy': '',
            'next_action': '',
            'reasoning': None,
            'human_review_required': None,
            'current_stage': None,
            'processing_result': None,
            'parsed_requirements': None,
            'project_creation_result': None
        }
        
        # REFACTORED: Use centralized services
        self.config_service = ConfigService.get_instance()
        self.config = config or self.config_service.get_llm_config()
        self.llm_service = LLMService()
        # Initialize DatabaseService with config values to avoid localhost fallback
        db_cfg = self.config_service.get_database_config() or {}
        self.db_service = DatabaseService.get_instance(
            uri=db_cfg.get('uri', 'mongodb://localhost:27017'),
            database=db_cfg.get('name', 'AIrecruiter'),
            timeout_ms=db_cfg.get('timeout_ms', 10000)
        )
        
        # Backward compatibility: expose llm_service.client as self.llm
        self.llm = self.llm_service.client
        
        # Logger (refactored to use get_logger)
        self.logger = get_logger('RecruitmentExecutiveAgent')
        
        # Lazy load legacy managers for backward compatibility
        self.sourcing_manager = None
        self.database_agent = None
        self.outreach_manager = None
        self._initialize_managers()
        
        self.logger.info("✅ RecruitmentExecutiveAgent initialized (using clean architecture services)")
    
    def _initialize_managers(self) -> None:
        """
        Initialize legacy manager agents for backward compatibility.
        
        REFACTORED: Simplified initialization since most operations now go through
        services (DatabaseService, LLMService). Managers kept for backward compatibility
        with existing code that may call them directly.
        
        Design Pattern:
            - Graceful Degradation: System continues if managers unavailable
            - Backward Compatibility: Existing code can still use managers
        """
        try:
            if UnifiedSourcingManager:
                self.sourcing_manager = UnifiedSourcingManager(
                    model_name=self.config.get('model', 'gpt-5'),
                    temperature=self.config.get('temperature', 0.3)
                )
                self.logger.debug("✅ UnifiedSourcingManager initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize SourcingManager: {e}")
        
        try:
            if DatabaseAgent:
                # Simplified: DatabaseAgent now just wraps DatabaseService
                self.database_agent = DatabaseAgent()
                self.logger.debug("✅ DatabaseAgent initialized (wrapper)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize DatabaseAgent: {e}")
        
        try:
            if OutreachManager:
                self.outreach_manager = OutreachManager()
                self.logger.debug("✅ OutreachManager initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize OutreachManager: {e}")


    def process_request_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """
        Process incoming recruitment request (workflow node).
        
        This is the entry point for all recruitment requests. It handles two
        distinct request types:
        
        1. **Frontend User Requests**: Natural language recruitment requests
           from users (e.g., "Find a senior Python developer")
        2. **LinkedIn API Webhooks**: Automated project creation when vacancies
           are posted on LinkedIn
        
        The method identifies the request source, extracts structured data,
        validates the input, and routes to appropriate processing handlers.
        All database operations are delegated to DatabaseAgent (monopoly pattern).
        
        Workflow:
            1. Identify request source (frontend_user | linkedin_api | unknown)
            2. Extract and structure request data
            3. Route to appropriate handler:
               - _process_user_request() for user requests
               - _process_linkedin_project() for API requests
               - _handle_unknown_request() for unrecognized requests
            4. Update state with processing results
            5. Set next_action for workflow routing
        
        Args:
            state: Current recruitment executive state containing request data
        
        Returns:
            Updated state with:
                - processing_result: Results from request processing
                - current_stage: Set to 'request_processed'
                - next_action: Set to 'analyze_request'
                - reasoning: List of processing steps (if any)
        
        Raises:
            No exceptions raised. Errors are caught, logged, and returned in
            state with error information.
        
        Example:
            >>> state = {
            ...     'user_request': 'Find Python developer',
            ...     'messages': [HumanMessage(content='Find Python developer')]
            ... }
            >>> updated_state = agent.process_request_node(state)
            >>> print(updated_state['current_stage'])
            'request_processed'
        
        Note:
            This method is designed to be used as a LangGraph workflow node.
            It updates state immutably and returns the updated state.
        """
        self.logger.info("Processing incoming request...")
        
        try:
            # Extract request information from state
            request_source = self._identify_request_source(state)
            request_data = self._extract_request_data(state)
            
            self.logger.info(f"Request source: {request_source}")
            self.logger.info(f"Request type: {request_data.get('type', 'unknown')}")
            
            # Process based on request source
            if request_source == "frontend_user":
                result = self._process_user_request(state, request_data)
            elif request_source == "linkedin_api":
                result = self._process_linkedin_project(state, request_data)
            else:
                result = self._handle_unknown_request(state, request_data)
            
            # Update state with processing results
            state['processing_result'] = result
            state['current_stage'] = 'request_processed'
            state['next_action'] = 'analyze_request'
            
            self.logger.info("Request processing completed")
            return state
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            state['next_action'] = 'error'
            state['reasoning'] = [f"Request processing failed: {str(e)}"]
            return state
    
    # ========================================================================
    # REQUEST PROCESSING METHODS
    # ========================================================================
    
    async def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recruitment workflow."""
        # Extract request text from various possible fields
        request_text = (
            request_data.get('request', '') or 
            request_data.get('user_request', '') or
            request_data.get('content', '') or
            str(request_data.get('request', ''))
        )
        
        # Set user_request in state
        self.state['user_request'] = request_text
        
        # Also add to messages if not empty
        if request_text and not self.state.get('messages'):
            from langchain_core.messages import HumanMessage
            self.state['messages'] = [HumanMessage(content=request_text)]
        
        result = self.process_request_node(self.state)
        return {
            'success': True,
            'result': result.get('processing_result', {}),
            'stage': result.get('current_stage')
        }
    
    def _identify_request_source(self, state: RecruitmentExecutiveState) -> str:
        """Identify whether request comes from frontend user or LinkedIn API.
        
        Args:
            state: Current state containing request information
            
        Returns:
            String indicating request source: 'frontend_user', 'linkedin_api', or 'unknown'
        """
        # First check user_request in state (most direct)
        user_request = state.get('user_request', '')
        
        # If no user_request, check messages
        if not user_request and state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'content') and last_message.content:
                user_request = last_message.content
            elif isinstance(last_message, dict):
                user_request = last_message.get('content', '')
        
        if not user_request:
            # Check for direct project data in state
            if state.get("linkedin_project_data"):
                return "linkedin_api"
            return "unknown"
        
        # Convert to string and lowercase for checking
        content = str(user_request).lower()
        
        # LinkedIn API indicators
        if any(indicator in content for indicator in [
            "linkedin_search_id", "saved_search", "api_created", 
            "project_id", "unipile", "linkedin_api"
        ]):
            return "linkedin_api"
        
        # User request indicators (recruitment keywords)
        recruitment_keywords = [
            "find", "recruit", "hire", "looking for", "need", "search for",
            "dev", "developer", "engineer", "candidate", "python", "java",
            "senior", "junior", "lead", "manager", "architect"
        ]
        if any(keyword in content for keyword in recruitment_keywords):
            return "frontend_user"
        
        # Check for direct project data in state
        if state.get("linkedin_project_data"):
            return "linkedin_api"
        
        # Default: if we have any text, assume it's a user request
        if user_request.strip():
            return "frontend_user"
        
        return "unknown"
    
    def _extract_request_data(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Extract and structure request data from state.
        
        Args:
            state: Current state
            
        Returns:
            Dictionary with structured request data
        """
        request_data = {
            "type": "unknown",
            "content": "",
            "request": "",
            "timestamp": datetime.now().isoformat(),
            "project_data": None,
            "user_requirements": None
        }
        
        # First check user_request in state (most direct)
        user_request = state.get('user_request', '')
        
        # If no user_request, try to extract from messages
        if not user_request and state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'content'):
                user_request = last_message.content
            elif isinstance(last_message, dict):
                user_request = last_message.get('content', '')
        
        if user_request:
            request_data["content"] = user_request
            request_data["request"] = user_request
            
            # Try to parse as JSON for API requests
            try:
                parsed_content = json.loads(user_request)
                if isinstance(parsed_content, dict):
                    request_data["project_data"] = parsed_content
                    request_data["type"] = "linkedin_project"
                    return request_data
            except (json.JSONDecodeError, TypeError):
                # It's a user text request
                request_data["user_requirements"] = user_request
                request_data["type"] = "user_request"
                return request_data
        
        # Extract from direct state data
        if state.get("linkedin_project_data"):
            request_data["project_data"] = state["linkedin_project_data"]
            request_data["type"] = "linkedin_project"
            return request_data
        
        return request_data
    
    def _process_user_request(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a frontend user recruitment request.
        
        REFACTORED: Now delegates to ProcessRecruitmentRequestUseCase.
        
        Args:
            state: Current state
            request_data: Extracted request information
            
        Returns:
            Dictionary with processing results
        """
        self.logger.info("👤 Processing frontend user request...")
        
        try:
            # Get user request from various possible fields
            user_request = (
                request_data.get("user_requirements", "") or
                request_data.get("request", "") or
                request_data.get("content", "")
            )
            
            # Delegate to use case
            use_case = ProcessRecruitmentRequestUseCase(
                db_service=self.db_service,
                llm_service=self.llm_service
            )
            
            # Execute use case (async)
            import asyncio
            result = asyncio.run(use_case.execute_user_request(user_request))
            
            # Transform use case result to expected format
            return {
                "processing_result": result.get("processing_result"),
                "user_request": [result.get("user_request")],
                "parsed_requirements": result.get("parsed_requirements"),
                "project_creation_needed": result.get("project_creation_needed"),
                "project_created": result.get("project_created", False),
                "project_id": result.get("project_id"),
                "reasoning": [
                    "User request delegated to ProcessRecruitmentRequestUseCase",
                    f"Project created: {result.get('project_created', False)}"
                ]
            }
            
        except ValidationError as e:
            self.logger.warning(f"⚠️ Validation error: {e}")
            return {
                "processing_result": "validation_failed",
                "reasoning": [str(e)],
                "human_review_required": True
            }
        except Exception as e:
            self.logger.error(f"❌ Error processing user request: {e}")
            return {
                "processing_result": "error",
                "reasoning": [f"Processing failed: {str(e)}"],
                "human_review_required": True
            }
    
    def _process_linkedin_project(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a LinkedIn API project creation request.
        
        REFACTORED: Now delegates to ProcessRecruitmentRequestUseCase.
        
        Args:
            state: Current state
            request_data: Project data from LinkedIn API
            
        Returns:
            Dictionary with processing results
        """
        self.logger.info("🔗 Processing LinkedIn API project...")
        
        try:
            project_data = request_data.get("project_data", {})
            
            # Delegate to use case
            use_case = ProcessRecruitmentRequestUseCase(
                db_service=self.db_service,
                llm_service=self.llm_service
            )
            
            # Execute use case (async)
            import asyncio
            result = asyncio.run(use_case.execute_linkedin_project(project_data))
            
            # Transform use case result to expected format
            return {
                "processing_result": result.get("processing_result"),
                "project_id": result.get("project_id"),
                "linkedin_search_id": result.get("linkedin_search_id"),
                "project_created": result.get("project_created", False),
                "reasoning": [
                    "LinkedIn project delegated to ProcessRecruitmentRequestUseCase",
                    f"Project created: {result.get('project_created', False)}",
                    f"Project ID: {result.get('project_id')}"
                ]
            }
            
        except ValidationError as e:
            self.logger.warning(f"⚠️ Validation error: {e}")
            return {
                "processing_result": "validation_failed",
                "reasoning": [str(e)],
                "human_review_required": True
            }
        except Exception as e:
            self.logger.error(f"❌ Error processing LinkedIn project: {e}")
            return {
                "processing_result": "error",
                "reasoning": [f"Processing failed: {str(e)}"],
                "human_review_required": True
            }
    
    def _handle_unknown_request(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests that don't match expected patterns.
        
        Args:
            state: Current state
            request_data: Request information
            
        Returns:
            Dictionary with error handling results
        """
        self.logger.warning("⚠️ Unknown request type received")
        
        return {
            "processing_result": "unknown_request",
            "reasoning": [
                "Request type could not be determined",
                "Manual review required to classify request",
                f"Content preview: {str(request_data.get('content', ''))[:100]}..."
            ],
            "human_review_required": True,
            "raw_request_data": request_data
        }
    
    # ============================================================================
    # WORKFLOW NODES - LangGraph integration
    # ============================================================================

    def analyze_request_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Analyze the user request and extract requirements."""
        logger.info(" Analyzing user request...")
        
        # Get the user request from messages
        user_request = ""
        if state.get("messages"):
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                user_request = last_message.content
        
        # Use the recruitment prompt
        prompt = RecruitmentPrompts.user_request_prompt(user_request)
        
        # Process with LLM
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Update state
        state["user_request"] = [user_request]
        state["next_action"] = "get_projects"
        
        # Add AI response to messages
        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(response)
        
        logger.info("Request analysis completed")
        return state
    
    def get_projects_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Retrieve relevant projects from the database via DatabaseAgent."""
        logger.info("📋 Retrieving projects via DatabaseAgent...")
        
        try:
            # Initialize DatabaseAgent to retrieve projects
            from agents.database_agent import DatabaseAgent, DatabaseAgentState
            
            # Create DatabaseAgent state
            db_state = DatabaseAgentState(
                name="ProjectRetrieval_DatabaseAgent",
                description="Database operations for project retrieval",
                tools=[], tool_descriptions=[], tool_input_types=[], tool_output_types=[],
                input_type="dict", output_type="dict", intermediate_steps=[],
                max_iterations=5, iteration_count=0, stop=False,
                last_action="", last_observation="", last_input="", last_output="",
                graph=None, memory=[], memory_limit=100, verbose=False,
                temperature=0.7, top_k=50, top_p=0.9, frequency_penalty=0.0, presence_penalty=0.0,
                best_of=1, n=1, logit_bias={}, seed=42, model=os.getenv("OPENAI_MODEL", "gpt-5"), api_key=""
            )
            
            db_agent = DatabaseAgent(db_state)
            
            # Retrieve projects via DatabaseAgent (all projects, no filter)
            projects = db_agent.list_projects()
            
            # Sync each project with LinkedIn to get fresh data
            logger.info(f"🔄 Syncing {len(projects)} projects with LinkedIn...")
            synced_projects = []
            for project in projects:
                try:
                    project_id = project.get('project_id', project.get('_id'))
                    if project_id:
                        synced_project = db_agent.sync_project_with_linkedin(project_id)
                        synced_projects.append(synced_project)
                    else:
                        logger.warning(f"⚠️ Project missing project_id, skipping sync: {project}")
                        synced_projects.append(project)
                except Exception as sync_error:
                    logger.error(f"❌ Failed to sync project {project.get('project_id')}: {sync_error}")
                    # Keep original project if sync fails
                    synced_projects.append(project)
            
            # Convert to standardized format
            formatted_projects = [convert_project_to_json(project) for project in synced_projects]
            
            state["current_projects"] = formatted_projects
            state["next_action"] = "plan_strategy"
            
            logger.info(f"✅ Retrieved and synced {len(formatted_projects)} projects via DatabaseAgent")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve projects via DatabaseAgent: {e}")
            logger.info("Fallback: Using legacy get_all_projects...")
            try:
                # Fallback to legacy method for backward compatibility
                projects = get_all_projects(use_mongodb=False, fallback=True)
                formatted_projects = [convert_project_to_json(project) for project in projects]
                state["current_projects"] = formatted_projects
            except Exception as fallback_e:
                logger.error(f"❌ Error retrieving projects (both DatabaseAgent and fallback failed): {fallback_e}")
                state["current_projects"] = []
            
            state["next_action"] = "plan_strategy"
        
        return state
    
    def plan_strategy_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Plan the recruitment strategy based on request and available projects."""
        logger.info("Planning recruitment strategy...")
        
        user_request = state.get("user_request", [""])[0] if state.get("user_request") else ""
        projects = state.get("current_projects", [])
        
        # Simple strategy planning (can be enhanced with LLM)
        if "urgent" in user_request.lower():
            strategy = "fast_track"
            next_action = "sourcing"
        elif "bulk" in user_request.lower() or any(str(i) in user_request for i in range(2, 20)):
            strategy = "bulk_hiring"
            next_action = "sourcing"
        else:
            strategy = "standard_recruitment"
            next_action = "sourcing"
        
        state["recruitment_strategy"] = strategy
        state["next_action"] = next_action
        
        # Initialize candidate pipeline
        if not state.get("candidate_pipeline"):
            state["candidate_pipeline"] = {
                "sourced": [],
                "contacted": [],
                "responded": [],
                "interviewed": [],
                "hired": []
            }
        
        logger.info(f" Strategy planned: {strategy}")
        return state
    
    def delegate_sourcing_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Delegate sourcing tasks to the Sourcing Manager.
        
        This node coordinates with the SourcingManager to find candidates based on:
        - Parsed requirements from user request
        - Available projects in the database
        - Current recruitment strategy
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with sourcing results
        """
        self.logger.info("🔍 Delegating to Sourcing Manager...")
        
        try:
            # REFACTORED: Use ExecuteSourcingWorkflowUseCase
            use_case = ExecuteSourcingWorkflowUseCase(sourcing_manager=self.sourcing_manager)
            
            import asyncio
            processed_results = asyncio.run(use_case.execute(state))
            
            # Update candidate pipeline with sourced candidates
            if not state.get("candidate_pipeline"):
                state["candidate_pipeline"] = {
                    "sourced": [],
                    "contacted": [],
                    "responded": [],
                    "interviewed": [],
                    "hired": []
                }
            
            state["candidate_pipeline"]["sourced"] = processed_results.get("candidates", [])
            state["sourcing_status"] = processed_results.get("status", "completed")
            state["sourcing_metrics"] = processed_results.get("metrics", {})
            
            # Determine next action based on sourcing results
            if processed_results.get("success", False) and len(processed_results.get("candidates", [])) > 0:
                state["next_action"] = "outreach"
                state["reasoning"] = [
                    f"Sourcing completed successfully",
                    f"Found {len(processed_results.get('candidates', []))} candidates",
                    "Proceeding to outreach phase"
                ]
            else:
                state["next_action"] = "sourcing_review"
                state["human_review_required"] = True
                state["reasoning"] = [
                    "Sourcing completed but with limited results",
                    "Human review required to adjust strategy"
                ]
            
            self.logger.info(f"✅ Sourcing delegation completed: {len(processed_results.get('candidates', []))} candidates found")
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Sourcing delegation failed: {e}")
            state["next_action"] = "error"
            state["sourcing_status"] = "failed"
            state["reasoning"] = [f"Sourcing delegation failed: {str(e)}"]
            return state
    
    def delegate_outreach_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Delegate outreach tasks to the Outreach Manager.
        
        This node coordinates with the OutreachManager to contact candidates:
        - Prioritizes candidates based on fit score
        - Manages multi-channel outreach (LinkedIn, Email, InMail)
        - Tracks response rates and engagement
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with outreach results
        """
        self.logger.info("📤 Delegating to Outreach Manager...")
        
        try:
            # REFACTORED: Use ExecuteOutreachCampaignUseCase
            use_case = ExecuteOutreachCampaignUseCase(outreach_manager=self.outreach_manager)
            
            import asyncio
            processed_outreach = asyncio.run(use_case.execute(state))
            
            # Update candidate pipeline
            pipeline = state.get("candidate_pipeline", {})
            pipeline["contacted"] = processed_outreach.get("contacted_candidates", [])
            pipeline["responded"] = processed_outreach.get("responded_candidates", [])
            
            # Update outreach metrics
            state["outreach_status"] = processed_outreach.get("status", "in_progress")
            state["outreach_metrics"] = processed_outreach.get("metrics", {})
            state["active_campaigns"] = processed_outreach.get("campaigns", [])
            
            # Determine next action
            if processed_outreach.get("requires_monitoring", True):
                state["next_action"] = "monitor"
                state["reasoning"] = [
                    "Outreach campaign initiated",
                    f"Contacted {len(processed_outreach.get('contacted_candidates', []))} candidates",
                    "Entering monitoring phase for responses"
                ]
            else:
                state["next_action"] = "complete"
                state["reasoning"] = [
                    "Outreach campaign completed",
                    "No monitoring required"
                ]
            
            self.logger.info(f"✅ Outreach delegation completed: {len(processed_outreach.get('contacted_candidates', []))} candidates contacted")
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Outreach delegation failed: {e}")
            state["next_action"] = "error"
            state["outreach_status"] = "failed"
            state["reasoning"] = [f"Outreach delegation failed: {str(e)}"]
            return state
    
    def monitor_progress_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Monitor the progress of the recruitment campaign.
        
        This node continuously monitors:
        - Sourcing Manager progress and results
        - Outreach Manager campaign performance
        - Candidate pipeline progression
        - Overall recruitment metrics
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with monitoring results
        """
        self.logger.info("📊 Monitoring recruitment progress...")
        
        try:
            # REFACTORED: Use MonitorProgressUseCase
            use_case = MonitorProgressUseCase()
            import asyncio
            monitoring_results = asyncio.run(use_case.execute(state))
            
            # Extract results from use case
            monitoring_data = monitoring_results.get("monitoring_results", {})
            next_action = monitoring_results.get("next_action", "report")
            
            # Update state with monitoring results
            state["monitoring_results"] = monitoring_data
            
            # Determine next action based on monitoring results
            if monitoring_results.get("status") == "error":
                state["next_action"] = "error"
                state["reasoning"] = [f"Progress monitoring failed: {monitoring_results.get('error', 'Unknown error')}"]
            elif next_action == "report":
                # Check if intervention needed
                needs_intervention = monitoring_data.get("needs_intervention", False)
                if needs_intervention:
                    state["next_action"] = "intervention"
                    state["human_review_required"] = True
                    state["reasoning"] = [
                        "Monitoring detected issues requiring intervention",
                        f"Pipeline health: {monitoring_data.get('progress_metrics', {}).get('pipeline_health', 'unknown')}"
                    ]
                else:
                    state["next_action"] = "complete"
                    progress_metrics = monitoring_data.get("progress_metrics", {})
                    state["reasoning"] = [
                        "Monitoring completed - generating final report",
                        f"Total candidates sourced: {progress_metrics.get('total_sourced', 0)}",
                        f"Total responses: {progress_metrics.get('total_responded', 0)}"
                    ]
            else:  # continue
                state["next_action"] = "monitor"
                progress_metrics = monitoring_data.get("progress_metrics", {})
                state["reasoning"] = [
                    "Monitoring continues - campaign in progress",
                    f"Response rate: {progress_metrics.get('response_rate', 0):.1f}%",
                    f"Pipeline health: {progress_metrics.get('pipeline_health', 'unknown')}"
                ]
            
            pipeline_health = monitoring_data.get("progress_metrics", {}).get("pipeline_health", "unknown")
            self.logger.info(f"📈 Monitoring completed: {pipeline_health} pipeline health")
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Monitoring failed: {e}")
            state["next_action"] = "error"
            state["reasoning"] = [f"Progress monitoring failed: {str(e)}"]
            return state
    
    def generate_report_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Generate comprehensive recruitment campaign report.
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with generated report
        """
        self.logger.info("📊 Generating comprehensive recruitment report...")
        
        try:
            # REFACTORED: Use GenerateReportUseCase
            use_case = GenerateReportUseCase()
            import asyncio
            report_results = asyncio.run(use_case.execute(state))
            
            # Update state with report results
            state["final_report"] = report_results.get("final_report", {})
            state["report_generated"] = report_results.get("report_generated", False)
            state["workflow_complete"] = report_results.get("workflow_complete", False)
            
            if report_results.get("status") == "error":
                state["report_error"] = report_results.get("report_error", "Unknown error")
            
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Report generation failed: {e}")
            state["report_error"] = str(e)
            return state
    
    # ---- Conditional Logic ----
    def route_next_step(self, state: RecruitmentExecutiveState) -> str:
        """Determine the next step in the workflow."""
        next_action = state.get("next_action", "sourcing")
        
        if next_action == "sourcing":
            return "sourcing"
        elif next_action == "outreach":
            return "outreach"
        elif next_action == "monitor":
            return "monitor"
        else:
            return "complete"
    
    def should_continue_monitoring(self, state: RecruitmentExecutiveState) -> str:
        """Determine if monitoring should continue or complete."""
        next_action = state.get("next_action", "complete")
        
        if next_action == "continue":
            return "continue"
        else:
            return "complete"
    
    def run(self, user_request: str) -> Dict[str, Any]:
        """Run the complete recruitment workflow."""
        logger.info(f" Starting recruitment workflow for: {user_request}")
        
        # Initialize state
        initial_state = RecruitmentExecutiveState(
            messages=[HumanMessage(content=user_request)],
            user_request=None,
            current_projects=None,
            active_campaigns=None,
            candidate_pipeline={},
            recruitment_strategy="",
            next_action=""
        )
        
        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            
            logger.info("Recruitment workflow completed successfully")
            return {
                "success": True,
                "final_state": final_state,
                "candidate_pipeline": final_state.get("candidate_pipeline", {}),
                "strategy": final_state.get("recruitment_strategy", ""),
                "messages": [msg.content for msg in final_state.get("messages", [])]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "partial_state": {}
            }

# # Factory function for easy import
# def create_recruitment_flow(config: Dict[str, Any] = None) -> RecruitmentExecutiveFlow:
#     """Create and return a configured RecruitmentExecutiveFlow."""
#     return RecruitmentExecutiveFlow(config)