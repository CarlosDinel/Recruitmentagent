"""
Recruitment Executive Orchestrator - Clean Architecture

This orchestrator coordinates the recruitment workflow using Clean Architecture principles.
It uses domain entities, repository interfaces, and use cases instead of direct
database access or manager agents.

Architecture:
============

    RecruitmentExecutiveOrchestrator
    ├── Uses Domain Entities (RecruitmentRequest, Project, Candidate)
    ├── Uses Repository Interfaces (ProjectRepository, CandidateRepository)
    ├── Coordinates Use Cases
    │   ├── ProcessRecruitmentRequestUseCase
    │   ├── CreateProjectUseCase
    │   ├── SearchCandidatesUseCase
    │   └── ExecuteOutreachCampaignUseCase
    └── Manages Workflow State

Design Principles:
=================

1. **Dependency Inversion**: Depends on abstractions (repositories), not implementations
2. **Single Responsibility**: Orchestrates, doesn't implement business logic
3. **Use Case Coordination**: Delegates to use cases for business operations
4. **Domain-Driven**: Uses domain entities, not dictionaries

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

# Domain Layer (inner layer - no dependencies)
from ...domain.entities.recruitment_request import RecruitmentRequest
from ...domain.entities.project import Project
from ...domain.entities.candidate import Candidate
from ...domain.value_objects.project_id import ProjectId
from ...domain.value_objects.candidate_id import CandidateId
from ...domain.value_objects.skill_set import SkillSet
from ...domain.enums.workflow_stage import WorkflowStage
from ...domain.repositories.project_repository import ProjectRepository
from ...domain.repositories.candidate_repository import CandidateRepository
from ...domain.repositories.campaign_repository import CampaignRepository

# Application Layer - Use Cases
from ..use_cases.sourcing.search_candidates import (
    SearchCandidatesUseCase,
    SearchCandidatesRequest
)

# Infrastructure Layer (injected via dependency injection)
# Note: We depend on interfaces, not implementations
# In a full Clean Architecture, we'd have a LinkedInService interface in domain
# For now, we use the implementation directly (can be refactored later)
try:
    from ...infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
except ImportError:
    # Fallback if not available
    LinkedInServiceImpl = None

logger = logging.getLogger(__name__)


class RecruitmentExecutiveOrchestrator:
    """
    Clean Architecture orchestrator for recruitment workflow.
    
    This orchestrator follows Clean Architecture principles:
    - Uses domain entities (RecruitmentRequest, Project, Candidate)
    - Depends on repository interfaces, not implementations
    - Coordinates use cases instead of implementing business logic
    - No direct database access
    - No direct external service calls (goes through interfaces)
    
    Responsibilities:
        - Coordinate recruitment workflow
        - Manage workflow state
        - Delegate to use cases
        - Handle workflow routing
    
    Dependencies (injected):
        - project_repository: ProjectRepository interface
        - candidate_repository: CandidateRepository interface
        - campaign_repository: CampaignRepository interface
        - linkedin_service: LinkedIn service interface
        - search_candidates_use_case: SearchCandidatesUseCase
    
    Example:
        >>> from src.infrastructure.persistence.mongodb import (
        ...     MongoDBProjectRepository,
        ...     MongoDBCandidateRepository
        ... )
        >>> from src.infrastructure.external_services.linkedin import LinkedInServiceImpl
        >>> 
        >>> # Initialize repositories (infrastructure)
        >>> project_repo = MongoDBProjectRepository()
        >>> candidate_repo = MongoDBCandidateRepository()
        >>> linkedin_service = LinkedInServiceImpl()
        >>> 
        >>> # Initialize use case
        >>> search_use_case = SearchCandidatesUseCase(
        ...     candidate_repository=candidate_repo,
        ...     linkedin_service=linkedin_service,
        ...     ai_service=None  # Will be injected
        ... )
        >>> 
        >>> # Initialize orchestrator with dependencies
        >>> orchestrator = RecruitmentExecutiveOrchestrator(
        ...     project_repository=project_repo,
        ...     candidate_repository=candidate_repo,
        ...     campaign_repository=None,  # Optional
        ...     linkedin_service=linkedin_service,
        ...     search_candidates_use_case=search_use_case
        ... )
        >>> 
        >>> # Process a request
        >>> result = await orchestrator.process_recruitment_request(
        ...     request_text="Find a senior Python developer"
        ... )
    
    Note:
        This is the Clean Architecture version. The old RecruitmentExecutiveAgent
        in agents/ folder will be kept for backward compatibility during migration.
    """
    
    def __init__(
        self,
        project_repository: ProjectRepository,
        candidate_repository: CandidateRepository,
        linkedin_service: LinkedInServiceImpl,
        campaign_repository: Optional[CampaignRepository] = None,
        search_candidates_use_case: Optional[SearchCandidatesUseCase] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the orchestrator with dependencies.
        
        Args:
            project_repository: Repository for project persistence
            candidate_repository: Repository for candidate persistence
            linkedin_service: LinkedIn service for external API calls
            campaign_repository: Optional repository for campaign persistence
            search_candidates_use_case: Optional use case for candidate search
            config: Optional configuration dictionary
        
        Design:
            - Dependency Injection: All dependencies injected
            - Interface Segregation: Depends on interfaces, not implementations
            - Single Responsibility: Only orchestrates, doesn't implement
        """
        self.project_repository = project_repository
        self.candidate_repository = candidate_repository
        self.campaign_repository = campaign_repository
        self.linkedin_service = linkedin_service
        self.search_candidates_use_case = search_candidates_use_case
        self.config = config or {}
        self.logger = logging.getLogger('RecruitmentExecutiveOrchestrator')
        self.logger.setLevel(logging.INFO)
        
        # Workflow state
        self.current_request: Optional[RecruitmentRequest] = None
        self.current_project: Optional[Project] = None
    
    async def process_recruitment_request(
        self,
        request_text: str,
        source: str = 'frontend_user'
    ) -> Dict[str, Any]:
        """
        Process a recruitment request using Clean Architecture.
        
        This method:
        1. Creates a RecruitmentRequest domain entity
        2. Parses requirements using domain logic
        3. Creates a Project entity if needed
        4. Delegates to use cases for operations
        
        Args:
            request_text: User request text
            source: Request source ('frontend_user' or 'linkedin_api')
        
        Returns:
            Dictionary with processing results
        
        Example:
            >>> result = await orchestrator.process_recruitment_request(
            ...     "Find a senior Python developer with 5+ years experience"
            ... )
            >>> print(result['project_id'])
        """
        self.logger.info(f"Processing recruitment request: {request_text[:50]}...")
        
        try:
            # Create domain entity
            request = self._create_recruitment_request(request_text, source)
            self.current_request = request
            
            # Parse requirements (domain logic)
            parsed_requirements = self._parse_requirements(request_text)
            
            # Create project if needed
            project = None
            if self._should_create_project(parsed_requirements):
                project = await self._create_project_from_request(request, parsed_requirements)
                self.current_project = project
            
            return {
                'success': True,
                'request_id': request.id,
                'project_id': project.id if project else None,
                'parsed_requirements': parsed_requirements,
                'stage': 'request_processed'
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'error'
            }
    
    def _create_recruitment_request(
        self,
        request_text: str,
        source: str
    ) -> RecruitmentRequest:
        """Create RecruitmentRequest domain entity."""
        # Parse basic info from request
        parsed = self._parse_requirements(request_text)
        
        return RecruitmentRequest(
            id=f"req_{uuid.uuid4().hex[:8]}",
            position=parsed.get('position', 'Developer'),
            company=parsed.get('company', 'Company'),
            description=request_text,
            required_skills=SkillSet(parsed.get('skills', [])),
            source=source,
            location=parsed.get('location'),
            experience_required=parsed.get('experience_required'),
            target_candidate_count=parsed.get('target_count', 50),
            urgency=parsed.get('urgency', 'normal')
        )
    
    def _parse_requirements(self, request_text: str) -> Dict[str, Any]:
        """Parse requirements from request text (simple implementation)."""
        text_lower = request_text.lower()
        
        # Extract position
        position = 'Developer'
        for role in ['developer', 'engineer', 'scientist', 'manager', 'architect']:
            if role in text_lower:
                position = role.title()
                break
        
        # Extract skills
        skills = []
        skill_keywords = ['python', 'javascript', 'react', 'django', 'aws', 'docker']
        for skill in skill_keywords:
            if skill in text_lower:
                skills.append(skill.title())
        
        # Extract location
        location = None
        location_keywords = ['amsterdam', 'rotterdam', 'utrecht', 'netherlands']
        for loc in location_keywords:
            if loc in text_lower:
                location = loc.title()
                break
        
        # Extract experience
        experience_required = None
        if '5+' in request_text or 'five' in text_lower:
            experience_required = 5
        elif '3+' in request_text or 'three' in text_lower:
            experience_required = 3
        
        return {
            'position': position,
            'skills': skills,
            'location': location,
            'experience_required': experience_required,
            'target_count': 50,
            'urgency': 'normal'
        }
    
    def _should_create_project(self, requirements: Dict[str, Any]) -> bool:
        """Determine if a project should be created."""
        return bool(requirements.get('position') or requirements.get('location'))
    
    async def _create_project_from_request(
        self,
        request: RecruitmentRequest,
        requirements: Dict[str, Any]
    ) -> Project:
        """Create Project domain entity from request."""
        from ...domain.value_objects.project_id import ProjectId
        
        project = Project(
            id=ProjectId(f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            title=f"{requirements.get('position', 'Position')} - {requirements.get('location', 'Location')}",
            company=request.company,
            description=request.description,
            requirements=request.description,
            skills_needed=request.required_skills,
            stage=WorkflowStage.REQUEST_RECEIVED,
            location=requirements.get('location'),
            experience_required=requirements.get('experience_required'),
            target_candidate_count=request.target_candidate_count,
            source=request.source
        )
        
        # Save via repository
        await self.project_repository.save(project)
        self.logger.info(f"Created project: {project.id}")
        
        return project
    
    async def execute_sourcing(
        self,
        project_id: str,
        search_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute candidate sourcing using use case.
        
        Args:
            project_id: Project identifier
            search_criteria: Search criteria dictionary
        
        Returns:
            Sourcing results
        """
        if not self.search_candidates_use_case:
            raise ValueError("SearchCandidatesUseCase not provided")
        
        request = SearchCandidatesRequest(
            project_id=project_id,
            search_criteria=search_criteria,
            max_results=50
        )
        
        response = await self.search_candidates_use_case.execute(request)
        
        return {
            'success': True,
            'candidates_found': response.total_found,
            'candidates': [c.to_dict() for c in response.candidates],
            'metadata': response.search_metadata
        }

