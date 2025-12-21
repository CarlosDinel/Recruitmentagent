"""
Recruitment Agent System - Multi-Agent Architecture

This package implements a hierarchical multi-agent system for automated recruitment.
The architecture follows the Orchestrator-Manager-SubAgent pattern with clear
separation of concerns and dependency injection.

Architecture Overview:
=====================

    ┌─────────────────────────────────────────────────────────────┐
    │           RecruitmentExecutiveAgent (Orchestrator)          │
    │  - Coordinates entire recruitment workflow                   │
    │  - Manages state and routing                                │
    │  - Delegates to specialized managers                        │
    └───────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │Sourcing │   │ Outreach │   │ Database │
    │ Manager │   │ Manager  │   │  Agent   │
    └────┬────┘   └────┬─────┘   └────┬─────┘
         │             │              │
         ▼             ▼              ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │Search   │   │LinkedIn  │   │MongoDB   │
    │Agent    │   │Outreach  │   │Tools     │
    │Eval     │   │Email     │   │          │
    │Agent    │   │Agent     │   │          │
    └─────────┘   └──────────┘   └──────────┘

Design Principles:
==================

1. **Single Responsibility**: Each agent has one clear purpose
2. **Dependency Injection**: Managers are injected, not hard-coded
3. **State Management**: TypedDict-based state objects for type safety
4. **Error Resilience**: Graceful degradation with fallback strategies
5. **Database Monopoly**: All DB operations go through DatabaseAgent
6. **Lazy Initialization**: Managers loaded on-demand to avoid circular imports

Agent Responsibilities:
=======================

RecruitmentExecutiveAgent:
    - Orchestrates end-to-end recruitment workflow
    - Processes user requests and LinkedIn API webhooks
    - Routes to appropriate managers based on workflow stage
    - Manages candidate pipeline state
    - Generates recruitment reports

UnifiedSourcingManager:
    - Coordinates candidate discovery pipeline
    - Manages search, evaluation, and enrichment phases
    - Implements AI-powered decision making
    - Handles retry logic and quality thresholds
    - Integrates with LinkedIn API via Unipile

OutreachManager:
    - Executes multi-channel outreach campaigns
    - Manages LinkedIn, Email, and InMail channels
    - Tracks campaign performance and metrics
    - Calculates engagement scores
    - Handles follow-up sequences

DatabaseAgent:
    - Exclusive database access (monopoly pattern)
    - Manages projects and candidates
    - Provides validation and structuring
    - Handles MongoDB operations
    - Ensures data consistency

Usage Example:
==============

    from agents import RecruitmentExecutiveAgent
    
    # Initialize the orchestrator
    agent = RecruitmentExecutiveAgent()
    
    # Process a recruitment request
    result = await agent.execute({
        'request': 'Find a senior Python developer'
    })
    
    # Access managers
    sourcing = agent.sourcing_manager
    outreach = agent.outreach_manager

Version: 1.0.0
Author: Senior Development Team
License: MIT
"""

from agents.recruitment_executive import (
    RecruitmentExecutiveAgent,
    RecruitmentExecutiveState,
    get_ai_config
)

from agents.sourcing_manager_unified import (
    UnifiedSourcingManager,
    CandidateRecord,
    SourcingManagerDecision,
    WorkflowStage
)

from agents.outreach_manager import (
    OutreachManager,
    OutreachManagerAgent  # Alias for backward compatibility
)

from agents.database_agent import (
    DatabaseAgent,
    DatabaseAgentState
)

__all__ = [
    # Main orchestrator
    'RecruitmentExecutiveAgent',
    'RecruitmentExecutiveState',
    'get_ai_config',
    
    # Sourcing
    'UnifiedSourcingManager',
    'CandidateRecord',
    'SourcingManagerDecision',
    'WorkflowStage',
    
    # Outreach
    'OutreachManager',
    'OutreachManagerAgent',
    
    # Database
    'DatabaseAgent',
    'DatabaseAgentState',
]

__version__ = '1.0.0'
__author__ = 'Senior Development Team'

