"""
Evaluate Candidates Use Case - Clean Architecture

This use case evaluates candidates against project requirements using domain services.
It follows Clean Architecture principles by using domain entities and services.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ....domain.entities.candidate import Candidate
from ....domain.entities.project import Project
from ....domain.value_objects.evaluation_score import EvaluationScore
from ....domain.enums.candidate_status import CandidateStatus
from ....domain.enums.evaluation_result import EvaluationResult
from ....domain.repositories.candidate_repository import CandidateRepository
from ....domain.services.candidate_evaluation_service import CandidateEvaluationService

logger = logging.getLogger(__name__)


class EvaluateCandidatesRequest:
    """Request DTO for evaluating candidates."""
    
    def __init__(
        self,
        candidates: List[Candidate],
        project: Project,
        evaluation_criteria: Optional[Dict[str, Any]] = None,
        job_description: Optional[str] = None
    ):
        self.candidates = candidates
        self.project = project
        self.evaluation_criteria = evaluation_criteria or {}
        self.job_description = job_description or project.description


class EvaluateCandidatesResponse:
    """Response DTO for candidate evaluation."""
    
    def __init__(
        self,
        evaluated_candidates: List[Candidate],
        suitable_candidates: List[Candidate],
        potentially_suitable: List[Candidate],
        not_suitable: List[Candidate],
        evaluation_metadata: Dict[str, Any]
    ):
        self.evaluated_candidates = evaluated_candidates
        self.suitable_candidates = suitable_candidates
        self.potentially_suitable = potentially_suitable
        self.not_suitable = not_suitable
        self.evaluation_metadata = evaluation_metadata


class EvaluateCandidatesUseCase:
    """
    Use case for evaluating candidates against project requirements.
    
    This use case uses the CandidateEvaluationService (domain service) to evaluate
    candidates. It follows Clean Architecture by keeping business logic in the
    domain layer and only orchestrating here.
    
    Example:
        >>> use_case = EvaluateCandidatesUseCase(
        ...     candidate_repository=candidate_repo,
        ...     evaluation_service=CandidateEvaluationService()
        ... )
        >>> 
        >>> request = EvaluateCandidatesRequest(
        ...     candidates=[candidate1, candidate2],
        ...     project=project,
        ...     evaluation_criteria={'quality_threshold': 70.0}
        ... )
        >>> 
        >>> response = await use_case.execute(request)
        >>> print(f"Suitable: {len(response.suitable_candidates)}")
    """
    
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        evaluation_service: Optional[CandidateEvaluationService] = None
    ):
        """
        Initialize evaluate candidates use case.
        
        Args:
            candidate_repository: Repository for candidate persistence
            evaluation_service: Optional domain service (creates default if not provided)
        """
        self.candidate_repository = candidate_repository
        self.evaluation_service = evaluation_service or CandidateEvaluationService()
        logger.info("EvaluateCandidatesUseCase initialized")
    
    async def execute(self, request: EvaluateCandidatesRequest) -> EvaluateCandidatesResponse:
        """
        Execute candidate evaluation.
        
        Args:
            request: Evaluation request with candidates and project
        
        Returns:
            Evaluation response with categorized candidates
        """
        logger.info(f"Evaluating {len(request.candidates)} candidates for project {request.project.id}")
        
        try:
            suitable_candidates = []
            potentially_suitable = []
            not_suitable = []
            
            quality_threshold = request.evaluation_criteria.get('quality_threshold', 70.0)
            medium_threshold = request.evaluation_criteria.get('medium_threshold', 50.0)
            
            for candidate in request.candidates:
                try:
                    # Use domain service for evaluation
                    evaluation_score = CandidateEvaluationService.evaluate_candidate(
                        candidate=candidate,
                        project=request.project,
                        evaluation_criteria=request.evaluation_criteria
                    )
                    
                    # Update candidate with evaluation
                    candidate.evaluate(evaluation_score)
                    
                    # Categorize based on score
                    if evaluation_score.overall_score >= quality_threshold:
                        candidate.update_status(CandidateStatus.SUITABLE)
                        suitable_candidates.append(candidate)
                    elif evaluation_score.overall_score >= medium_threshold:
                        candidate.update_status(CandidateStatus.POTENTIALLY_SUITABLE)
                        potentially_suitable.append(candidate)
                    else:
                        candidate.update_status(CandidateStatus.UNSUITABLE)
                        not_suitable.append(candidate)
                    
                    # Save updated candidate
                    await self.candidate_repository.save(candidate)
                    
                except Exception as e:
                    logger.warning(f"Error evaluating candidate {candidate.id}: {e}")
                    continue
            
            evaluation_metadata = {
                "project_id": str(request.project.id),
                "total_evaluated": len(request.candidates),
                "suitable_count": len(suitable_candidates),
                "potentially_suitable_count": len(potentially_suitable),
                "not_suitable_count": len(not_suitable),
                "evaluation_timestamp": datetime.now().isoformat(),
                "quality_threshold": quality_threshold,
                "medium_threshold": medium_threshold
            }
            
            logger.info(
                f"Evaluation completed: {len(suitable_candidates)} suitable, "
                f"{len(potentially_suitable)} potentially suitable, "
                f"{len(not_suitable)} not suitable"
            )
            
            return EvaluateCandidatesResponse(
                evaluated_candidates=request.candidates,
                suitable_candidates=suitable_candidates,
                potentially_suitable=potentially_suitable,
                not_suitable=not_suitable,
                evaluation_metadata=evaluation_metadata
            )
            
        except Exception as e:
            logger.error(f"Error executing candidate evaluation: {e}")
            raise

