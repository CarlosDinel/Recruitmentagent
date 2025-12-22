"""
State management for the Sourcing Manager agent orchestration.

This module defines the state schema for coordinating sub-agents in the sourcing pipeline:
- CandidateSearchingAgent: LinkedIn search and basic enrichment
- CandidateEvaluationAgent: Suitability assessment and decision making  
- ProfileScrapingAgent: Detailed profile enrichment

State tracks the complete candidate journey from search to evaluation to enrichment.
"""

from typing import List, Dict, Any, Optional, TypedDict, Literal
from datetime import datetime
from pydantic import BaseModel


class CandidateRecord(BaseModel):
    """Individual candidate data structure"""
    candidate_id: str
    linkedin_url: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    experience_years: Optional[int] = None
    skills: List[str] = []
    education: List[Dict[str, Any]] = []
    contact_info: Dict[str, str] = {}
    
    # Search metadata
    search_score: Optional[float] = None
    search_source: Optional[str] = None
    search_timestamp: Optional[datetime] = None
    
    # Evaluation metadata  
    suitability_status: Optional[Literal["suitable", "unsuitable", "maybe"]] = None
    suitability_score: Optional[float] = None
    suitability_reasoning: Optional[str] = None
    evaluation_timestamp: Optional[datetime] = None
    
    # Scraping metadata
    profile_enriched: bool = False
    enrichment_timestamp: Optional[datetime] = None
    enrichment_details: Dict[str, Any] = {}


class SourcingWorkflowState(TypedDict):
    """Complete state for Sourcing Manager orchestration"""
    
    # Request information
    request_id: str
    project_requirements: Dict[str, Any]
    job_description: str
    target_count: int
    search_criteria: Dict[str, Any]
    
    # Workflow tracking
    current_stage: Literal["searching", "evaluating", "enriching", "completed", "error"]
    stages_completed: List[str]
    
    # Candidate pipeline
    candidates_found: List[CandidateRecord]
    candidates_evaluated: List[CandidateRecord] 
    candidates_enriched: List[CandidateRecord]
    candidates_final: List[CandidateRecord]
    
    # Agent delegation tracking
    search_agent_status: Literal["pending", "running", "completed", "error"]
    evaluation_agent_status: Literal["pending", "running", "completed", "error"]
    scraping_agent_status: Literal["pending", "running", "completed", "error"]
    
    # Results and metrics
    total_found: int
    total_suitable: int
    total_enriched: int
    success_rate: float
    
    # Error handling
    errors: List[Dict[str, Any]]
    warnings: List[str]
    
    # Timing metadata
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # Agent communication
    agent_messages: List[Dict[str, Any]]
    intermediate_results: Dict[str, Any]


class SourcingManagerDecision(BaseModel):
    """Decision framework for workflow orchestration"""
    action: Literal["search", "evaluate", "enrich", "complete", "retry", "abort"]
    target_agent: Optional[str] = None
    reasoning: str
    confidence: float
    next_steps: List[str]
    estimated_duration: Optional[int] = None  # minutes


class AgentDelegationRequest(BaseModel):
    """Standardized request format for sub-agent delegation"""
    agent_name: str
    request_type: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]
    expected_output: str
    timeout_minutes: int = 30


class AgentDelegationResponse(BaseModel):
    """Standardized response format from sub-agents"""
    agent_name: str
    status: Literal["success", "error", "timeout"]
    result: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None
    warnings: List[str] = []


def create_initial_sourcing_state(
    request_id: str,
    project_requirements: Dict[str, Any],
    job_description: str,
    target_count: int = 50
) -> SourcingWorkflowState:
    """Create initial state for sourcing workflow"""
    now = datetime.now()
    
    return SourcingWorkflowState(
        request_id=request_id,
        project_requirements=project_requirements,
        job_description=job_description,
        target_count=target_count,
        search_criteria={},
        
        current_stage="searching",
        stages_completed=[],
        
        candidates_found=[],
        candidates_evaluated=[],
        candidates_enriched=[],
        candidates_final=[],
        
        search_agent_status="pending",
        evaluation_agent_status="pending", 
        scraping_agent_status="pending",
        
        total_found=0,
        total_suitable=0,
        total_enriched=0,
        success_rate=0.0,
        
        errors=[],
        warnings=[],
        
        started_at=now,
        updated_at=now,
        completed_at=None,
        
        agent_messages=[],
        intermediate_results={}
    )


def update_workflow_stage(
    state: SourcingWorkflowState,
    new_stage: str,
    agent_status_updates: Optional[Dict[str, str]] = None
) -> SourcingWorkflowState:
    """Update workflow stage and agent statuses"""
    state["current_stage"] = new_stage
    state["updated_at"] = datetime.now()
    
    if new_stage not in state["stages_completed"]:
        state["stages_completed"].append(new_stage)
    
    if agent_status_updates:
        for agent, status in agent_status_updates.items():
            if f"{agent}_status" in state:
                state[f"{agent}_status"] = status
    
    return state


def calculate_success_metrics(state: SourcingWorkflowState) -> SourcingWorkflowState:
    """Calculate and update success metrics"""
    state["total_found"] = len(state["candidates_found"])
    state["total_suitable"] = len([c for c in state["candidates_evaluated"] 
                                  if c.suitability_status == "suitable"])
    state["total_enriched"] = len(state["candidates_enriched"])
    
    if state["total_found"] > 0:
        state["success_rate"] = state["total_suitable"] / state["total_found"]
    else:
        state["success_rate"] = 0.0
    
    return state