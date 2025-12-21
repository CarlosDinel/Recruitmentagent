"""Search Candidates Use Case."""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ....domain.entities.candidate import Candidate
from ....domain.value_objects import CandidateId, ProjectId, SkillSet, ContactInfo
from ....domain.enums import CandidateStatus
from ....domain.repositories.candidate_repository import CandidateRepository

logger = logging.getLogger(__name__)


class SearchCandidatesRequest:
    """Request DTO for searching candidates."""
    
    def __init__(
        self,
        project_id: str,
        search_criteria: Dict[str, Any],
        max_results: int = 50,
        location: Optional[str] = None,
        keywords: Optional[str] = None,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        skills: Optional[List[str]] = None,
        experience_level: Optional[str] = None
    ):
        self.project_id = project_id
        self.search_criteria = search_criteria
        self.max_results = max_results
        self.location = location
        self.keywords = keywords
        self.company_name = company_name
        self.job_title = job_title
        self.skills = skills or []
        self.experience_level = experience_level


class SearchCandidatesResponse:
    """Response DTO for candidate search."""
    
    def __init__(
        self,
        candidates: List[Candidate],
        total_found: int,
        search_metadata: Dict[str, Any]
    ):
        self.candidates = candidates
        self.total_found = total_found
        self.search_metadata = search_metadata


class SearchCandidatesUseCase:
    """Use case for searching candidates on LinkedIn."""
    
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        linkedin_service: Any,  # LinkedIn service interface
        ai_service: Any  # AI service interface
    ):
        """
        Initialize search candidates use case.
        
        Args:
            candidate_repository: Repository for candidate persistence
            linkedin_service: Service for LinkedIn API interactions
            ai_service: Service for AI/LLM interactions
        """
        self.candidate_repository = candidate_repository
        self.linkedin_service = linkedin_service
        self.ai_service = ai_service
        logger.info("SearchCandidatesUseCase initialized")
    
    async def execute(self, request: SearchCandidatesRequest) -> SearchCandidatesResponse:
        """
        Execute candidate search.
        
        Args:
            request: Search request with criteria
            
        Returns:
            Search response with candidates
        """
        logger.info(f"Executing candidate search for project {request.project_id}")
        
        try:
            # Search LinkedIn using service
            search_results = self.linkedin_service.search_candidates(
                query=request.keywords,
                location=request.location,
                company=request.company_name,
                title=request.job_title,
                skills=request.skills,
                limit=request.max_results
            )
            
            # Convert search results to domain entities
            candidates = self._convert_to_candidates(
                search_results.get('data', []),
                request.project_id
            )
            
            # Check for existing candidates (deduplication)
            unique_candidates = []
            for candidate in candidates:
                exists = await self.candidate_repository.exists_by_linkedin_url(
                    candidate.contact_info.linkedin_url or ""
                )
                if not exists:
                    unique_candidates.append(candidate)
            
            # Save new candidates
            if unique_candidates:
                await self.candidate_repository.batch_save(unique_candidates)
            
            search_metadata = {
                "project_id": request.project_id,
                "total_found": len(candidates),
                "unique_candidates": len(unique_candidates),
                "search_timestamp": datetime.now().isoformat(),
                "search_criteria": request.search_criteria
            }
            
            logger.info(f"Search completed: {len(unique_candidates)} new candidates found")
            
            return SearchCandidatesResponse(
                candidates=unique_candidates,
                total_found=len(candidates),
                search_metadata=search_metadata
            )
            
        except Exception as e:
            logger.error(f"Error executing candidate search: {e}")
            raise
    
    def _convert_to_candidates(
        self,
        search_data: List[Dict[str, Any]],
        project_id: str
    ) -> List[Candidate]:
        """Convert LinkedIn search results to Candidate entities."""
        candidates = []
        
        for data in search_data:
            try:
                # Extract LinkedIn URL
                linkedin_url = data.get('linkedin_url') or data.get('profile_url') or data.get('url')
                
                if not linkedin_url:
                    continue
                
                # Generate candidate ID from LinkedIn URL
                candidate_id = CandidateId.from_linkedin_url(linkedin_url)
                
                # Extract contact info
                contact_info = ContactInfo(
                    email=data.get('email'),
                    phone=data.get('phone'),
                    linkedin_url=linkedin_url
                )
                
                # Extract skills
                skills_list = data.get('skills', []) or data.get('skill_list', [])
                skills = SkillSet(skills_list if isinstance(skills_list, list) else [])
                
                # Create candidate entity
                candidate = Candidate(
                    id=candidate_id,
                    name=data.get('name') or data.get('full_name', 'Unknown'),
                    current_position=data.get('title') or data.get('current_position'),
                    current_company=data.get('company') or data.get('current_company'),
                    location=data.get('location'),
                    contact_info=contact_info,
                    skills=skills,
                    years_experience=data.get('experience_years') or data.get('years_experience'),
                    education=data.get('education'),
                    status=CandidateStatus.NEW,
                    profile_data=data,
                    source='linkedin_search',
                    project_id=project_id
                )
                
                candidates.append(candidate)
                
            except Exception as e:
                logger.warning(f"Error converting search result to candidate: {e}")
                continue
        
        return candidates

