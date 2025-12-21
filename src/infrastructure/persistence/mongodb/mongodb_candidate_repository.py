"""MongoDB implementation of CandidateRepository."""

from typing import List, Optional
from datetime import datetime
import logging

from pymongo.errors import PyMongoError
from pymongo.collection import Collection

from ....domain.repositories.candidate_repository import CandidateRepository
from ....domain.entities.candidate import Candidate
from ....domain.value_objects import CandidateId, ProjectId, SkillSet, ContactInfo, EvaluationScore
from ....domain.enums import CandidateStatus

from .mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)


class MongoDBCandidateRepository(CandidateRepository):
    """MongoDB implementation of candidate repository."""
    
    def __init__(self, collection_name: str = "candidates"):
        """
        Initialize MongoDB candidate repository.
        
        Args:
            collection_name: Name of the MongoDB collection
        """
        self._client = MongoDBClient()
        self._collection: Collection = self._client.get_collection(collection_name)
        logger.info(f"Initialized MongoDBCandidateRepository with collection: {collection_name}")
    
    async def save(self, candidate: Candidate) -> CandidateId:
        """
        Save or update a candidate.
        
        Args:
            candidate: Candidate entity to save
            
        Returns:
            CandidateId of the saved candidate
        """
        try:
            document = self._entity_to_document(candidate)
            
            # Use LinkedIn URL as _id for deduplication, fallback to candidate ID
            doc_id = candidate.contact_info.linkedin_url or str(candidate.id)
            
            # Update or insert
            result = self._collection.replace_one(
                {"_id": doc_id},
                document,
                upsert=True
            )
            
            logger.info(f"Saved candidate: {candidate.id} (upserted: {result.upserted_id is not None})")
            return candidate.id
            
        except PyMongoError as e:
            logger.error(f"Error saving candidate {candidate.id}: {e}")
            raise
    
    async def find_by_id(self, candidate_id: CandidateId) -> Optional[Candidate]:
        """
        Find candidate by ID.
        
        Args:
            candidate_id: Unique candidate identifier
            
        Returns:
            Candidate if found, None otherwise
        """
        try:
            # Try to find by candidate ID (stored in document)
            document = self._collection.find_one({"candidate_id": str(candidate_id)})
            
            if not document:
                # Fallback: try as _id if it matches
                document = self._collection.find_one({"_id": str(candidate_id)})
            
            if document:
                return self._document_to_entity(document)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Error finding candidate {candidate_id}: {e}")
            return None
    
    async def find_by_linkedin_url(self, linkedin_url: str) -> Optional[Candidate]:
        """
        Find candidate by LinkedIn URL (for deduplication).
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Candidate if found, None otherwise
        """
        try:
            # LinkedIn URL is used as _id in MongoDB
            document = self._collection.find_one({"_id": linkedin_url})
            
            if not document:
                # Fallback: search in linkedin_url field
                document = self._collection.find_one({"linkedin_url": linkedin_url})
            
            if document:
                return self._document_to_entity(document)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Error finding candidate by LinkedIn URL {linkedin_url}: {e}")
            return None
    
    async def find_by_project(self, project_id: ProjectId) -> List[Candidate]:
        """
        Find all candidates for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of candidates
        """
        try:
            cursor = self._collection.find({
                "$or": [
                    {"project_id": str(project_id)},
                    {"projectid": str(project_id)}  # Support old format
                ]
            })
            
            candidates = []
            for document in cursor:
                try:
                    candidate = self._document_to_entity(document)
                    candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Error converting document to entity: {e}")
                    continue
            
            logger.info(f"Found {len(candidates)} candidates for project {project_id}")
            return candidates
            
        except PyMongoError as e:
            logger.error(f"Error finding candidates for project {project_id}: {e}")
            return []
    
    async def find_by_status(self, status: str, project_id: Optional[ProjectId] = None) -> List[Candidate]:
        """
        Find candidates by status, optionally filtered by project.
        
        Args:
            status: Candidate status
            project_id: Optional project filter
            
        Returns:
            List of candidates
        """
        try:
            query = {
                "$or": [
                    {"status": status},
                    {"Status": status}  # Support old format
                ]
            }
            
            if project_id:
                query["$and"] = [
                    query,
                    {
                        "$or": [
                            {"project_id": str(project_id)},
                            {"projectid": str(project_id)}
                        ]
                    }
                ]
            
            cursor = self._collection.find(query)
            
            candidates = []
            for document in cursor:
                try:
                    candidate = self._document_to_entity(document)
                    candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Error converting document to entity: {e}")
                    continue
            
            logger.info(f"Found {len(candidates)} candidates with status {status}")
            return candidates
            
        except PyMongoError as e:
            logger.error(f"Error finding candidates by status {status}: {e}")
            return []
    
    async def search_by_skills(self, skills: List[str], min_match: float = 0.5) -> List[Candidate]:
        """
        Search candidates by skills.
        
        Args:
            skills: Required skills
            min_match: Minimum match score (0.0 to 1.0)
            
        Returns:
            List of matching candidates
        """
        try:
            # MongoDB text search or array intersection
            # For now, use array intersection (candidates must have at least one skill)
            cursor = self._collection.find({
                "skills": {"$in": skills}
            })
            
            candidates = []
            required_skill_set = SkillSet(skills)
            
            for document in cursor:
                try:
                    candidate = self._document_to_entity(document)
                    # Calculate match score
                    match_score = candidate.skills.match_score(required_skill_set)
                    
                    if match_score >= min_match:
                        candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Error converting document to entity: {e}")
                    continue
            
            # Sort by match score (descending)
            candidates.sort(
                key=lambda c: c.skills.match_score(required_skill_set),
                reverse=True
            )
            
            logger.info(f"Found {len(candidates)} candidates matching skills {skills}")
            return candidates
            
        except PyMongoError as e:
            logger.error(f"Error searching candidates by skills: {e}")
            return []
    
    async def delete(self, candidate_id: CandidateId) -> bool:
        """
        Delete a candidate.
        
        Args:
            candidate_id: Candidate identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = self._collection.delete_one({
                "$or": [
                    {"candidate_id": str(candidate_id)},
                    {"_id": str(candidate_id)}
                ]
            })
            
            deleted = result.deleted_count > 0
            logger.info(f"Deleted candidate {candidate_id}: {deleted}")
            return deleted
            
        except PyMongoError as e:
            logger.error(f"Error deleting candidate {candidate_id}: {e}")
            return False
    
    async def exists_by_linkedin_url(self, linkedin_url: str) -> bool:
        """
        Check if candidate exists by LinkedIn URL.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            True if candidate exists
        """
        try:
            count = self._collection.count_documents({
                "$or": [
                    {"_id": linkedin_url},
                    {"linkedin_url": linkedin_url}
                ]
            })
            return count > 0
            
        except PyMongoError as e:
            logger.error(f"Error checking candidate existence: {e}")
            return False
    
    async def count_by_project(self, project_id: ProjectId, status: Optional[str] = None) -> int:
        """
        Count candidates for a project, optionally filtered by status.
        
        Args:
            project_id: Project identifier
            status: Optional status filter
            
        Returns:
            Number of candidates
        """
        try:
            query = {
                "$or": [
                    {"project_id": str(project_id)},
                    {"projectid": str(project_id)}
                ]
            }
            
            if status:
                query["$and"] = [
                    query,
                    {
                        "$or": [
                            {"status": status},
                            {"Status": status}
                        ]
                    }
                ]
            
            count = self._collection.count_documents(query)
            logger.debug(f"Counted {count} candidates for project {project_id}")
            return count
            
        except PyMongoError as e:
            logger.error(f"Error counting candidates: {e}")
            return 0
    
    async def batch_save(self, candidates: List[Candidate]) -> List[CandidateId]:
        """
        Save multiple candidates in batch.
        
        Args:
            candidates: List of candidates to save
            
        Returns:
            List of candidate IDs
        """
        try:
            operations = []
            candidate_ids = []
            
            for candidate in candidates:
                document = self._entity_to_document(candidate)
                doc_id = candidate.contact_info.linkedin_url or str(candidate.id)
                
                operations.append({
                    "replaceOne": {
                        "filter": {"_id": doc_id},
                        "replacement": document,
                        "upsert": True
                    }
                })
                candidate_ids.append(candidate.id)
            
            if operations:
                self._collection.bulk_write(operations)
                logger.info(f"Batch saved {len(candidates)} candidates")
            
            return candidate_ids
            
        except PyMongoError as e:
            logger.error(f"Error batch saving candidates: {e}")
            raise
    
    # Helper methods for conversion
    
    def _entity_to_document(self, candidate: Candidate) -> dict:
        """Convert domain entity to MongoDB document."""
        doc_id = candidate.contact_info.linkedin_url or str(candidate.id)
        
        document = {
            "_id": doc_id,
            "candidate_id": str(candidate.id),
            "name": candidate.name,
            "full_name": candidate.name,  # Support old format
            "current_position": candidate.current_position,
            "positie": candidate.current_position,  # Support old format
            "current_company": candidate.current_company,
            "location": candidate.location,
            "locatie": candidate.location,  # Support old format
            "email": candidate.contact_info.email,
            "phone": candidate.contact_info.phone,
            "linkedin_url": candidate.contact_info.linkedin_url,
            "skills": candidate.skills.to_list(),
            "years_experience": candidate.years_experience,
            "experience_years": candidate.years_experience,  # Support old format
            "education": candidate.education,
            "status": candidate.status.value,
            "Status": candidate.status.value,  # Support old format
            "project_id": candidate.project_id,
            "projectid": candidate.project_id,  # Support old format
            "campaign_id": candidate.campaign_id,
            "source": candidate.source or "SourcingManager",
            "created_at": candidate.created_at.isoformat() if isinstance(candidate.created_at, datetime) else candidate.created_at,
            "updated_at": candidate.updated_at.isoformat() if isinstance(candidate.updated_at, datetime) else candidate.updated_at,
            "last_updated": candidate.updated_at.isoformat() if isinstance(candidate.updated_at, datetime) else candidate.updated_at,
            "profile_data": candidate.profile_data,
        }
        
        # Add evaluation score if present
        if candidate.evaluation_score:
            document["evaluation_score"] = candidate.evaluation_score.to_dict()
            document["suitability_score"] = candidate.evaluation_score.overall_score
            document["suitability_reasoning"] = candidate.evaluation_score.reasoning
        
        return document
    
    def _document_to_entity(self, document: dict) -> Candidate:
        """Convert MongoDB document to domain entity."""
        # Extract candidate ID
        candidate_id_str = document.get("candidate_id") or document.get("_id")
        if not candidate_id_str:
            # Generate from LinkedIn URL if available
            linkedin_url = document.get("linkedin_url") or document.get("_id")
            if linkedin_url and "linkedin.com" in str(linkedin_url):
                candidate_id = CandidateId.from_linkedin_url(linkedin_url)
            else:
                candidate_id = CandidateId.generate()
        else:
            candidate_id = CandidateId(candidate_id_str)
        
        # Extract contact info
        contact_info = ContactInfo(
            email=document.get("email"),
            phone=document.get("phone"),
            linkedin_url=document.get("linkedin_url") or (document.get("_id") if "linkedin.com" in str(document.get("_id", "")) else None)
        )
        
        # Extract skills
        skills_list = document.get("skills", [])
        if not skills_list:
            skills_list = []
        skills = SkillSet(skills_list)
        
        # Extract status
        status_str = document.get("status") or document.get("Status", "new")
        try:
            status = CandidateStatus(status_str)
        except ValueError:
            # Map old status values to new enum
            status_mapping = {
                "Uncontacted": CandidateStatus.NEW,
                "Contacted": CandidateStatus.CONTACTED,
                "Responded": CandidateStatus.RESPONDED,
            }
            status = status_mapping.get(status_str, CandidateStatus.NEW)
        
        # Extract evaluation score
        evaluation_score = None
        if document.get("evaluation_score"):
            eval_data = document["evaluation_score"]
            evaluation_score = EvaluationScore(
                overall_score=eval_data.get("overall_score", eval_data.get("suitability_score", 0.0)),
                skill_match_score=eval_data.get("skill_match_score", 0.0),
                experience_score=eval_data.get("experience_score", 0.0),
                culture_fit_score=eval_data.get("culture_fit_score"),
                reasoning=eval_data.get("reasoning", eval_data.get("suitability_reasoning", ""))
            )
        elif document.get("suitability_score"):
            # Support old format
            evaluation_score = EvaluationScore(
                overall_score=document.get("suitability_score", 0.0),
                skill_match_score=0.0,
                experience_score=0.0,
                culture_fit_score=None,
                reasoning=document.get("suitability_reasoning", "")
            )
        
        # Extract dates
        created_at = document.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        updated_at = document.get("updated_at") or document.get("last_updated")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.now()
        
        return Candidate(
            id=candidate_id,
            name=document.get("name") or document.get("full_name", "Unknown"),
            current_position=document.get("current_position") or document.get("positie"),
            current_company=document.get("current_company"),
            location=document.get("location") or document.get("locatie"),
            contact_info=contact_info,
            skills=skills,
            years_experience=document.get("years_experience") or document.get("experience_years"),
            education=document.get("education"),
            status=status,
            evaluation_score=evaluation_score,
            profile_data=document.get("profile_data", {}),
            source=document.get("source"),
            created_at=created_at,
            updated_at=updated_at,
            project_id=document.get("project_id") or document.get("projectid"),
            campaign_id=document.get("campaign_id")
        )

