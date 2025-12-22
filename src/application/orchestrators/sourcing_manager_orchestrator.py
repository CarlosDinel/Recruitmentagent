"""
Sourcing Manager Orchestrator - Clean Architecture

This orchestrator coordinates the candidate sourcing pipeline using Clean Architecture
principles. It orchestrates use cases for searching, evaluating, and enriching candidates.

Architecture:
============

    SourcingManagerOrchestrator
    ├── Uses Domain Entities (Project, Candidate)
    ├── Uses Repository Interfaces (CandidateRepository, ProjectRepository)
    ├── Coordinates Use Cases
    │   ├── SearchCandidatesUseCase
    │   ├── EvaluateCandidatesUseCase (to be created)
    │   └── EnrichCandidateProfilesUseCase (to be created)
    └── Manages Sourcing Pipeline State

Design Principles:
=================

1. **Dependency Inversion**: Depends on abstractions (repositories), not implementations
2. **Single Responsibility**: Orchestrates sourcing pipeline, doesn't implement business logic
3. **Use Case Coordination**: Delegates to use cases for operations
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
from ...domain.entities.project import Project
from ...domain.entities.candidate import Candidate
from ...domain.value_objects.project_id import ProjectId
from ...domain.value_objects.candidate_id import CandidateId
from ...domain.enums.workflow_stage import WorkflowStage
from ...domain.enums.candidate_status import CandidateStatus
from ...domain.repositories.candidate_repository import CandidateRepository
from ...domain.repositories.project_repository import ProjectRepository
from ...domain.services.candidate_evaluation_service import CandidateEvaluationService

# Application Layer - Use Cases
from ..use_cases.sourcing.search_candidates import (
    SearchCandidatesUseCase,
    SearchCandidatesRequest,
    SearchCandidatesResponse
)

# Infrastructure Layer (injected via dependency injection)
try:
    from ...infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
except ImportError:
    LinkedInServiceImpl = None

logger = logging.getLogger(__name__)


class SourcingManagerOrchestrator:
    """
    Clean Architecture orchestrator for candidate sourcing pipeline.
    
    This orchestrator follows Clean Architecture principles:
    - Uses domain entities (Project, Candidate)
    - Depends on repository interfaces, not implementations
    - Coordinates use cases instead of implementing business logic
    - No direct database access
    - No direct external service calls (goes through interfaces)
    
    Responsibilities:
        - Coordinate candidate sourcing workflow
        - Manage sourcing pipeline state
        - Delegate to use cases (search, evaluate, enrich)
        - Enforce quality thresholds
        - Handle retry logic and error recovery
    
    Dependencies (injected):
        - candidate_repository: CandidateRepository interface
        - project_repository: ProjectRepository interface
        - linkedin_service: LinkedIn service interface
        - search_candidates_use_case: SearchCandidatesUseCase
        - candidate_evaluation_service: CandidateEvaluationService (domain service)
    
    Example:
        >>> from src.infrastructure.persistence.mongodb import (
        ...     MongoDBCandidateRepository,
        ...     MongoDBProjectRepository
        ... )
        >>> from src.infrastructure.external_services.linkedin import LinkedInServiceImpl
        >>> 
        >>> # Initialize repositories
        >>> candidate_repo = MongoDBCandidateRepository()
        >>> project_repo = MongoDBProjectRepository()
        >>> linkedin_service = LinkedInServiceImpl()
        >>> 
        >>> # Initialize use case
        >>> search_use_case = SearchCandidatesUseCase(
        ...     candidate_repository=candidate_repo,
        ...     linkedin_service=linkedin_service,
        ...     ai_service=None
        ... )
        >>> 
        >>> # Initialize domain service
        >>> evaluation_service = CandidateEvaluationService()
        >>> 
        >>> # Initialize orchestrator
        >>> orchestrator = SourcingManagerOrchestrator(
        ...     candidate_repository=candidate_repo,
        ...     project_repository=project_repo,
        ...     linkedin_service=linkedin_service,
        ...     search_candidates_use_case=search_use_case,
        ...     candidate_evaluation_service=evaluation_service
        ... )
        >>> 
        >>> # Execute sourcing
        >>> result = await orchestrator.process_sourcing_request(
        ...     project_id="proj123",
        ...     requirements={
        ...         'position': 'Python Developer',
        ...         'skills': ['Python', 'Django'],
        ...         'location': 'Amsterdam'
        ...     },
        ...     target_count=50
        ... )
    
    Note:
        This is the Clean Architecture version. The old UnifiedSourcingManager
        in agents/ folder will be kept for backward compatibility during migration.
    """
    
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        project_repository: ProjectRepository,
        linkedin_service: LinkedInServiceImpl,
        search_candidates_use_case: SearchCandidatesUseCase,
        candidate_evaluation_service: Optional[CandidateEvaluationService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the sourcing orchestrator with dependencies.
        
        Args:
            candidate_repository: Repository for candidate persistence
            project_repository: Repository for project persistence
            linkedin_service: LinkedIn service for external API calls
            search_candidates_use_case: Use case for candidate search
            candidate_evaluation_service: Optional domain service for evaluation
            config: Optional configuration dictionary
        
        Design:
            - Dependency Injection: All dependencies injected
            - Interface Segregation: Depends on interfaces, not implementations
            - Single Responsibility: Only orchestrates, doesn't implement
        """
        self.candidate_repository = candidate_repository
        self.project_repository = project_repository
        self.linkedin_service = linkedin_service
        self.search_candidates_use_case = search_candidates_use_case
        self.candidate_evaluation_service = candidate_evaluation_service or CandidateEvaluationService()
        self.config = config or {}
        self.logger = logging.getLogger('SourcingManagerOrchestrator')
        self.logger.setLevel(logging.INFO)
        
        # Pipeline configuration
        self.max_retries = self.config.get('max_retries', 3)
        self.min_candidates_threshold = self.config.get('min_candidates', 10)
        self.min_suitable_threshold = self.config.get('min_suitable', 5)
        self.quality_threshold = self.config.get('quality_threshold', 70.0)
        
        # Pipeline state
        self.current_project: Optional[Project] = None
        self.sourced_candidates: List[Candidate] = []
        self.evaluated_candidates: List[Candidate] = []
    
    async def process_sourcing_request(
        self,
        project_id: str,
        requirements: Dict[str, Any],
        job_description: Optional[str] = None,
        target_count: int = 50
    ) -> Dict[str, Any]:
        """
        Process a sourcing request using Clean Architecture.
        
        This method orchestrates the complete sourcing pipeline:
        1. Load project from repository
        2. Search candidates using use case
        3. Evaluate candidates using domain service
        4. Update project metrics
        5. Return sourcing results
        
        Args:
            project_id: Project identifier
            requirements: Sourcing requirements dictionary
            job_description: Optional job description for evaluation
            target_count: Target number of candidates to find
        
        Returns:
            Dictionary with sourcing results
        
        Example:
            >>> result = await orchestrator.process_sourcing_request(
            ...     project_id="proj123",
            ...     requirements={
            ...         'position': 'Python Developer',
            ...         'skills': ['Python', 'Django'],
            ...         'location': 'Amsterdam'
            ...     },
            ...     target_count=50
            ... )
            >>> print(f"Found {result['total_found']} candidates")
            >>> print(f"Suitable: {result['suitable_count']}")
        """
        self.logger.info(f"Processing sourcing request for project: {project_id}")
        
        try:
            # Load project from repository
            project = await self._load_project(project_id)
            if not project:
                return {
                    'success': False,
                    'error': f'Project {project_id} not found',
                    'stage': 'error'
                }
            
            self.current_project = project
            
            # Update project stage
            project.update_stage(WorkflowStage.SOURCING_STARTED)
            await self.project_repository.save(project)
            
            # Phase 1: Search candidates
            self.logger.info("Phase 1: Searching candidates...")
            search_result = await self._search_candidates(project, requirements, target_count)
            
            if not search_result['success']:
                return {
                    'success': False,
                    'error': search_result.get('error', 'Search failed'),
                    'stage': 'error'
                }
            
            self.sourced_candidates = search_result['candidates']
            self.logger.info(f"Found {len(self.sourced_candidates)} candidates")
            
            # Phase 2: Evaluate candidates
            self.logger.info("Phase 2: Evaluating candidates...")
            evaluation_result = await self._evaluate_candidates(
                self.sourced_candidates,
                project,
                job_description
            )
            
            self.evaluated_candidates = evaluation_result['suitable_candidates']
            self.logger.info(f"Evaluated: {len(self.evaluated_candidates)} suitable candidates")
            
            # Update project metrics
            project.update_candidate_metrics(
                found=len(self.sourced_candidates),
                suitable=len(self.evaluated_candidates)
            )
            
            # Check if we meet minimum requirements
            if len(self.evaluated_candidates) >= self.min_suitable_threshold:
                project.update_stage(WorkflowStage.SOURCING_COMPLETED)
            else:
                project.update_stage(WorkflowStage.OPTIMIZING)
                self.logger.warning(
                    f"Only {len(self.evaluated_candidates)} suitable candidates found, "
                    f"below threshold of {self.min_suitable_threshold}"
                )
            
            await self.project_repository.save(project)
            
            return {
                'success': True,
                'project_id': str(project.id),
                'total_found': len(self.sourced_candidates),
                'suitable_count': len(self.evaluated_candidates),
                'candidates': [c.to_dict() for c in self.evaluated_candidates],
                'stage': project.stage.value,
                'meets_threshold': len(self.evaluated_candidates) >= self.min_suitable_threshold
            }
            
        except Exception as e:
            self.logger.error(f"Error processing sourcing request: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stage': 'error'
            }
    
    async def _load_project(self, project_id: str) -> Optional[Project]:
        """Load project from repository."""
        try:
            project_id_obj = ProjectId(project_id)
            project = await self.project_repository.find_by_id(project_id_obj)
            return project
        except Exception as e:
            self.logger.error(f"Error loading project {project_id}: {e}")
            return None
    
    async def _search_candidates(
        self,
        project: Project,
        requirements: Dict[str, Any],
        target_count: int
    ) -> Dict[str, Any]:
        """Search candidates using use case."""
        try:
            # Prepare search request
            search_request = SearchCandidatesRequest(
                project_id=str(project.id),
                search_criteria=requirements,
                max_results=target_count,
                location=project.location,
                keywords=requirements.get('position'),
                job_title=requirements.get('position'),
                skills=project.skills_needed.to_list() if hasattr(project.skills_needed, 'to_list') else requirements.get('skills', []),
                experience_level=str(requirements.get('experience_required', ''))
            )
            
            # Execute use case
            search_response: SearchCandidatesResponse = await self.search_candidates_use_case.execute(search_request)
            
            return {
                'success': True,
                'candidates': search_response.candidates,
                'total_found': search_response.total_found,
                'metadata': search_response.search_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error searching candidates: {e}")
            return {
                'success': False,
                'error': str(e),
                'candidates': []
            }
    
    async def _evaluate_candidates(
        self,
        candidates: List[Candidate],
        project: Project,
        job_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate candidates using domain service."""
        suitable_candidates = []
        
        for candidate in candidates:
            try:
                # Use domain service for evaluation
                evaluation_score = CandidateEvaluationService.evaluate_candidate(
                    candidate=candidate,
                    project=project,
                    evaluation_criteria={}
                )
                
                # Update candidate with evaluation
                if evaluation_score.overall_score >= self.quality_threshold:
                    candidate.evaluate(evaluation_score)
                    candidate.update_status(CandidateStatus.SUITABLE)
                    suitable_candidates.append(candidate)
                    
                    # Save updated candidate
                    await self.candidate_repository.save(candidate)
                else:
                    candidate.evaluate(evaluation_score)
                    candidate.update_status(CandidateStatus.UNSUITABLE)
                    await self.candidate_repository.save(candidate)
                    
            except Exception as e:
                self.logger.warning(f"Error evaluating candidate {candidate.id}: {e}")
                continue
        
        return {
            'success': True,
            'suitable_candidates': suitable_candidates,
            'total_evaluated': len(candidates),
            'suitable_count': len(suitable_candidates)
        }

