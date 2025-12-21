"""MongoDB implementation of ProjectRepository."""

from typing import List, Optional
from datetime import datetime
import logging

from pymongo.errors import PyMongoError

from ....domain.repositories.project_repository import ProjectRepository
from ....domain.entities.project import Project
from ....domain.value_objects import ProjectId, SkillSet
from ....domain.enums import WorkflowStage

from .mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)


class MongoDBProjectRepository(ProjectRepository):
    """MongoDB implementation of project repository."""
    
    def __init__(self, collection_name: str = "projects"):
        """
        Initialize MongoDB project repository.
        
        Args:
            collection_name: Name of the MongoDB collection
        """
        self._client = MongoDBClient()
        self._collection = self._client.get_collection(collection_name)
        logger.info(f"Initialized MongoDBProjectRepository with collection: {collection_name}")
    
    async def save(self, project: Project) -> ProjectId:
        """
        Save or update a project.
        
        Args:
            project: Project entity to save
            
        Returns:
            ProjectId of the saved project
        """
        try:
            document = self._entity_to_document(project)
            project_id = str(project.id)
            
            # Update or insert
            result = self._collection.replace_one(
                {"_id": project_id},
                document,
                upsert=True
            )
            
            logger.info(f"Saved project: {project.id} (upserted: {result.upserted_id is not None})")
            return project.id
            
        except PyMongoError as e:
            logger.error(f"Error saving project {project.id}: {e}")
            raise
    
    async def find_by_id(self, project_id: ProjectId) -> Optional[Project]:
        """
        Find project by ID.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Project if found, None otherwise
        """
        try:
            document = self._collection.find_one({"_id": str(project_id)})
            
            if not document:
                # Fallback: try project_id field
                document = self._collection.find_one({"project_id": str(project_id)})
            
            if document:
                return self._document_to_entity(document)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Error finding project {project_id}: {e}")
            return None
    
    async def find_all_active(self) -> List[Project]:
        """
        Find all active projects.
        
        Returns:
            List of active projects
        """
        try:
            cursor = self._collection.find({
                "$or": [
                    {"is_active": True},
                    {"status": {"$ne": "deleted"}}  # Support old format
                ]
            })
            
            projects = []
            for document in cursor:
                try:
                    project = self._document_to_entity(document)
                    if project.is_active:
                        projects.append(project)
                except Exception as e:
                    logger.warning(f"Error converting document to entity: {e}")
                    continue
            
            logger.info(f"Found {len(projects)} active projects")
            return projects
            
        except PyMongoError as e:
            logger.error(f"Error finding active projects: {e}")
            return []
    
    async def find_by_stage(self, stage: str) -> List[Project]:
        """
        Find projects by workflow stage.
        
        Args:
            stage: Workflow stage
            
        Returns:
            List of projects
        """
        try:
            cursor = self._collection.find({
                "$or": [
                    {"stage": stage},
                    {"workflow_stage": stage}  # Support old format
                ]
            })
            
            projects = []
            for document in cursor:
                try:
                    project = self._document_to_entity(document)
                    projects.append(project)
                except Exception as e:
                    logger.warning(f"Error converting document to entity: {e}")
                    continue
            
            logger.info(f"Found {len(projects)} projects with stage {stage}")
            return projects
            
        except PyMongoError as e:
            logger.error(f"Error finding projects by stage {stage}: {e}")
            return []
    
    async def find_by_company(self, company: str) -> List[Project]:
        """
        Find projects by company name.
        
        Args:
            company: Company name
            
        Returns:
            List of projects
        """
        try:
            cursor = self._collection.find({
                "$or": [
                    {"company": company},
                    {"company_name": company}  # Support old format
                ]
            })
            
            projects = []
            for document in cursor:
                try:
                    project = self._document_to_entity(document)
                    projects.append(project)
                except Exception as e:
                    logger.warning(f"Error converting document to entity: {e}")
                    continue
            
            logger.info(f"Found {len(projects)} projects for company {company}")
            return projects
            
        except PyMongoError as e:
            logger.error(f"Error finding projects by company {company}: {e}")
            return []
    
    async def delete(self, project_id: ProjectId) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = self._collection.delete_one({
                "$or": [
                    {"_id": str(project_id)},
                    {"project_id": str(project_id)}
                ]
            })
            
            deleted = result.deleted_count > 0
            logger.info(f"Deleted project {project_id}: {deleted}")
            return deleted
            
        except PyMongoError as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            return False
    
    async def exists(self, project_id: ProjectId) -> bool:
        """
        Check if project exists.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if project exists
        """
        try:
            count = self._collection.count_documents({
                "$or": [
                    {"_id": str(project_id)},
                    {"project_id": str(project_id)}
                ]
            })
            return count > 0
            
        except PyMongoError as e:
            logger.error(f"Error checking project existence: {e}")
            return False
    
    async def count_active(self) -> int:
        """
        Count active projects.
        
        Returns:
            Number of active projects
        """
        try:
            count = self._collection.count_documents({
                "$or": [
                    {"is_active": True},
                    {"status": {"$ne": "deleted"}}
                ]
            })
            logger.debug(f"Counted {count} active projects")
            return count
            
        except PyMongoError as e:
            logger.error(f"Error counting active projects: {e}")
            return 0
    
    # Helper methods for conversion
    
    def _entity_to_document(self, project: Project) -> dict:
        """Convert domain entity to MongoDB document."""
        document = {
            "_id": str(project.id),
            "project_id": str(project.id),
            "title": project.title,
            "name": project.title,  # Support old format
            "company": project.company,
            "company_name": project.company,  # Support old format
            "description": project.description,
            "requirements": project.requirements,
            "skills_needed": project.skills_needed.to_list(),
            "skills": project.skills_needed.to_list(),  # Support old format
            "stage": project.stage.value,
            "workflow_stage": project.stage.value,  # Support old format
            "location": project.location,
            "experience_required": project.experience_required,
            "is_active": project.is_active,
            "status": "active" if project.is_active else "inactive",  # Support old format
            "target_candidate_count": project.target_candidate_count,
            "min_suitable_candidates": project.min_suitable_candidates,
            "source": project.source,
            "created_at": project.created_at.isoformat() if isinstance(project.created_at, datetime) else project.created_at,
            "updated_at": project.updated_at.isoformat() if isinstance(project.updated_at, datetime) else project.updated_at,
            "candidates_found": project.candidates_found,
            "candidates_suitable": project.candidates_suitable,
            "candidates_contacted": project.candidates_contacted,
            "candidates_responded": project.candidates_responded,
            "additional_data": project.additional_data,
        }
        
        if project.completed_at:
            document["completed_at"] = project.completed_at.isoformat() if isinstance(project.completed_at, datetime) else project.completed_at
        
        return document
    
    def _document_to_entity(self, document: dict) -> Project:
        """Convert MongoDB document to domain entity."""
        from ....domain.value_objects import ProjectId
        
        # Extract project ID
        project_id_str = document.get("_id") or document.get("project_id")
        if not project_id_str:
            raise ValueError("Project document missing ID")
        project_id = ProjectId(project_id_str)
        
        # Extract skills
        skills_list = document.get("skills_needed") or document.get("skills", [])
        skills = SkillSet(skills_list if skills_list else [])
        
        # Extract stage
        stage_str = document.get("stage") or document.get("workflow_stage", "new")
        try:
            stage = WorkflowStage(stage_str)
        except ValueError:
            # Map old stage values
            stage_mapping = {
                "active": WorkflowStage.SOURCING,
                "inactive": WorkflowStage.COMPLETED,
            }
            stage = stage_mapping.get(stage_str, WorkflowStage.NEW)
        
        # Extract dates
        created_at = document.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        updated_at = document.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.now()
        
        completed_at = document.get("completed_at")
        if completed_at:
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            elif not isinstance(completed_at, datetime):
                completed_at = None
        else:
            completed_at = None
        
        # Determine if active
        is_active = document.get("is_active")
        if is_active is None:
            # Fallback to status field
            status = document.get("status", "active")
            is_active = status != "deleted" and status != "inactive"
        
        return Project(
            id=project_id,
            title=document.get("title") or document.get("name", "Untitled Project"),
            company=document.get("company") or document.get("company_name", "Unknown"),
            description=document.get("description", ""),
            requirements=document.get("requirements", ""),
            skills_needed=skills,
            stage=stage,
            location=document.get("location"),
            experience_required=document.get("experience_required"),
            is_active=is_active,
            target_candidate_count=document.get("target_candidate_count", 50),
            min_suitable_candidates=document.get("min_suitable_candidates", 5),
            source=document.get("source"),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            additional_data=document.get("additional_data", {}),
            candidates_found=document.get("candidates_found", 0),
            candidates_suitable=document.get("candidates_suitable", 0),
            candidates_contacted=document.get("candidates_contacted", 0),
            candidates_responded=document.get("candidates_responded", 0),
        )

