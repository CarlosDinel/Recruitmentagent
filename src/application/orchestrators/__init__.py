"""
Application Orchestrators - Clean Architecture

This module contains orchestrators that coordinate use cases and manage
workflow state. Orchestrators are part of the Application layer and
depend on Domain entities and repositories.

Orchestrators:
- RecruitmentExecutiveOrchestrator: Main recruitment workflow coordinator
- SourcingManagerOrchestrator: Candidate sourcing pipeline coordinator
- OutreachManagerOrchestrator: Outreach campaign coordinator
"""

from .recruitment_executive_orchestrator import RecruitmentExecutiveOrchestrator
from .sourcing_manager_orchestrator import SourcingManagerOrchestrator
from .outreach_manager_orchestrator import OutreachManagerOrchestrator

__all__ = [
    'RecruitmentExecutiveOrchestrator',
    'SourcingManagerOrchestrator',
    'OutreachManagerOrchestrator',
]
