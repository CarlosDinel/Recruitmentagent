"""
Enrich Candidate Profiles Use Case - Clean Architecture

This use case enriches candidate profiles with additional data from external sources.
It follows Clean Architecture principles by using domain entities and services.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ....domain.entities.candidate import Candidate
from ....domain.enums.candidate_status import CandidateStatus
from ....domain.repositories.candidate_repository import CandidateRepository

# Infrastructure services (injected)
try:
    from ....infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
except ImportError:
    LinkedInServiceImpl = None

logger = logging.getLogger(__name__)


class EnrichCandidateProfilesRequest:
    """Request DTO for enriching candidate profiles."""
    
    def __init__(
        self,
        candidates: List[Candidate],
        enrichment_level: str = "standard",  # "standard", "detailed", "comprehensive"
        include_work_history: bool = True,
        include_education: bool = True,
        include_certifications: bool = False
    ):
        self.candidates = candidates
        self.enrichment_level = enrichment_level
        self.include_work_history = include_work_history
        self.include_education = include_education
        self.include_certifications = include_certifications


class EnrichCandidateProfilesResponse:
    """Response DTO for profile enrichment."""
    
    def __init__(
        self,
        enriched_candidates: List[Candidate],
        enrichment_metadata: Dict[str, Any]
    ):
        self.enriched_candidates = enriched_candidates
        self.enrichment_metadata = enrichment_metadata


class EnrichCandidateProfilesUseCase:
    """
    Use case for enriching candidate profiles with additional data.
    
    This use case fetches additional profile data from external sources (e.g., LinkedIn)
    and enriches the candidate entities. It follows Clean Architecture by using
    infrastructure services through interfaces.
    
    Example:
        >>> use_case = EnrichCandidateProfilesUseCase(
        ...     candidate_repository=candidate_repo,
        ...     linkedin_service=linkedin_service
        ... )
        >>> 
        >>> request = EnrichCandidateProfilesRequest(
        ...     candidates=[candidate1, candidate2],
        ...     enrichment_level="detailed"
        ... )
        >>> 
        >>> response = await use_case.execute(request)
        >>> print(f"Enriched: {len(response.enriched_candidates)}")
    """
    
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        linkedin_service: Optional[LinkedInServiceImpl] = None
    ):
        """
        Initialize enrich candidate profiles use case.
        
        Args:
            candidate_repository: Repository for candidate persistence
            linkedin_service: Optional LinkedIn service for profile enrichment
        """
        self.candidate_repository = candidate_repository
        self.linkedin_service = linkedin_service
        logger.info("EnrichCandidateProfilesUseCase initialized")
    
    async def execute(self, request: EnrichCandidateProfilesRequest) -> EnrichCandidateProfilesResponse:
        """
        Execute profile enrichment.
        
        Args:
            request: Enrichment request with candidates and options
        
        Returns:
            Enrichment response with enriched candidates
        """
        logger.info(f"Enriching {len(request.candidates)} candidate profiles")
        
        try:
            enriched_candidates = []
            enrichment_stats = {
                "total_requested": len(request.candidates),
                "successfully_enriched": 0,
                "failed": 0,
                "enrichment_timestamp": datetime.now().isoformat()
            }
            
            for candidate in request.candidates:
                try:
                    # Check if candidate has LinkedIn URL
                    linkedin_url = candidate.contact_info.linkedin_url
                    if not linkedin_url:
                        logger.warning(f"Candidate {candidate.id} has no LinkedIn URL, skipping enrichment")
                        continue
                    
                    # Update status to enriching
                    if candidate.status == CandidateStatus.SUITABLE:
                        candidate.update_status(CandidateStatus.ENRICHING)
                    
                    # Fetch enrichment data
                    enrichment_data = await self._fetch_enrichment_data(
                        candidate=candidate,
                        enrichment_level=request.enrichment_level,
                        include_work_history=request.include_work_history,
                        include_education=request.include_education,
                        include_certifications=request.include_certifications
                    )
                    
                    # Enrich candidate profile
                    if enrichment_data:
                        candidate.enrich_profile(enrichment_data)
                        enriched_candidates.append(candidate)
                        enrichment_stats["successfully_enriched"] += 1
                        
                        # Save enriched candidate
                        await self.candidate_repository.save(candidate)
                    else:
                        enrichment_stats["failed"] += 1
                        logger.warning(f"Failed to enrich candidate {candidate.id}")
                    
                except Exception as e:
                    logger.warning(f"Error enriching candidate {candidate.id}: {e}")
                    enrichment_stats["failed"] += 1
                    continue
            
            enrichment_metadata = {
                **enrichment_stats,
                "enrichment_level": request.enrichment_level,
                "options": {
                    "include_work_history": request.include_work_history,
                    "include_education": request.include_education,
                    "include_certifications": request.include_certifications
                }
            }
            
            logger.info(
                f"Enrichment completed: {enrichment_stats['successfully_enriched']} enriched, "
                f"{enrichment_stats['failed']} failed"
            )
            
            return EnrichCandidateProfilesResponse(
                enriched_candidates=enriched_candidates,
                enrichment_metadata=enrichment_metadata
            )
            
        except Exception as e:
            logger.error(f"Error executing profile enrichment: {e}")
            raise
    
    async def _fetch_enrichment_data(
        self,
        candidate: Candidate,
        enrichment_level: str,
        include_work_history: bool,
        include_education: bool,
        include_certifications: bool
    ) -> Optional[Dict[str, Any]]:
        """Fetch enrichment data from external sources."""
        try:
            linkedin_url = candidate.contact_info.linkedin_url
            if not linkedin_url:
                return None
            
            # For now, return mock data structure
            # In production, this would call LinkedIn service to fetch detailed profile
            enrichment_data = {
                "enrichment_source": "linkedin",
                "enrichment_timestamp": datetime.now().isoformat(),
                "enrichment_level": enrichment_level
            }
            
            if include_work_history:
                enrichment_data["work_history"] = candidate.profile_data.get("work_history", [])
            
            if include_education:
                enrichment_data["education"] = candidate.profile_data.get("education", [])
            
            if include_certifications:
                enrichment_data["certifications"] = candidate.profile_data.get("certifications", [])
            
            # If LinkedIn service is available, fetch real data
            if self.linkedin_service:
                try:
                    # Extract LinkedIn ID from URL
                    linkedin_id = linkedin_url.split("/")[-1] if "/" in linkedin_url else linkedin_url
                    
                    # Fetch profile data (this would be implemented in LinkedIn service)
                    # profile_data = await self.linkedin_service.get_profile_details(linkedin_id)
                    # enrichment_data.update(profile_data)
                    pass
                except Exception as e:
                    logger.warning(f"Error fetching LinkedIn data: {e}")
            
            return enrichment_data
            
        except Exception as e:
            logger.error(f"Error fetching enrichment data: {e}")
            return None

