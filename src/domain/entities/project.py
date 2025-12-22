"""Project Entity - Recruitment Project"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..value_objects import ProjectId, SkillSet
from ..enums import WorkflowStage


@dataclass
class Project:
    """
    Project entity representing a recruitment project.
    A project groups candidates for a specific job position.
    """
    
    # Identity
    id: ProjectId
    
    # Basic Info
    title: str
    company: str
    description: str
    
    # Requirements
    requirements: str
    skills_needed: SkillSet
    
    # Status
    stage: WorkflowStage
    
    # Required fields without defaults must come before optional fields
    location: Optional[str] = None
    experience_required: Optional[int] = None
    is_active: bool = True
    
    # Targets
    target_candidate_count: int = 50
    min_suitable_candidates: int = 5
    
    # Metadata
    source: Optional[str] = None  # 'frontend_user' or 'linkedin_api'
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Additional Data
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    candidates_found: int = 0
    candidates_suitable: int = 0
    candidates_contacted: int = 0
    candidates_responded: int = 0
    
    def __post_init__(self):
        """Validate project data."""
        if not self.title or not self.title.strip():
            raise ValueError("Project title cannot be empty")
        
        if not self.company or not self.company.strip():
            raise ValueError("Company name cannot be empty")
        
        if self.target_candidate_count < 1:
            raise ValueError("Target candidate count must be at least 1")
        
        if self.min_suitable_candidates < 1:
            raise ValueError("Minimum suitable candidates must be at least 1")
        
        if self.experience_required is not None and self.experience_required < 0:
            raise ValueError("Experience required cannot be negative")
    
    # Business Logic Methods
    
    def update_stage(self, new_stage: WorkflowStage) -> None:
        """Update project workflow stage."""
        if not self.is_active:
            raise ValueError("Cannot update stage of inactive project")
        
        if new_stage.is_terminal():
            self.is_active = False
            self.completed_at = datetime.now()
        
        self.stage = new_stage
        self.updated_at = datetime.now()
    
    def update_candidate_metrics(
        self,
        found: Optional[int] = None,
        suitable: Optional[int] = None,
        contacted: Optional[int] = None,
        responded: Optional[int] = None
    ) -> None:
        """Update candidate metrics."""
        if found is not None:
            self.candidates_found = found
        if suitable is not None:
            self.candidates_suitable = suitable
        if contacted is not None:
            self.candidates_contacted = contacted
        if responded is not None:
            self.candidates_responded = responded
        
        self.updated_at = datetime.now()
    
    def meets_minimum_requirements(self) -> bool:
        """Check if project has met minimum suitable candidates requirement."""
        return self.candidates_suitable >= self.min_suitable_candidates
    
    def is_sourcing_complete(self) -> bool:
        """Check if sourcing phase is complete."""
        return (
            self.stage in [
                WorkflowStage.SOURCING_COMPLETED,
                WorkflowStage.OUTREACH_STARTED,
                WorkflowStage.OUTREACH_COMPLETED
            ] or 
            self.candidates_found >= self.target_candidate_count
        )
    
    def is_outreach_active(self) -> bool:
        """Check if project is in outreach phase."""
        return self.stage.is_outreach_stage()
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate (suitable / found)."""
        if self.candidates_found == 0:
            return 0.0
        return self.candidates_suitable / self.candidates_found
    
    def calculate_response_rate(self) -> float:
        """Calculate response rate (responded / contacted)."""
        if self.candidates_contacted == 0:
            return 0.0
        return self.candidates_responded / self.candidates_contacted
    
    def matches_candidate_skills(self, candidate_skills: List[str], min_match: float = 0.5) -> bool:
        """Check if candidate skills match project requirements."""
        candidate_skill_set = SkillSet(candidate_skills)
        match_score = candidate_skill_set.match_score(self.skills_needed)
        return match_score >= min_match
    
    def complete_project(self, reason: str = "completed") -> None:
        """Mark project as completed."""
        if reason == "success":
            self.update_stage(WorkflowStage.COMPLETED)
        elif reason == "cancelled":
            self.update_stage(WorkflowStage.CANCELLED)
        else:
            self.update_stage(WorkflowStage.FAILED)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            'id': str(self.id),
            'title': self.title,
            'company': self.company,
            'description': self.description,
            'requirements': self.requirements,
            'skills_needed': self.skills_needed.to_list(),
            'location': self.location,
            'experience_required': self.experience_required,
            'stage': self.stage.value,
            'is_active': self.is_active,
            'target_candidate_count': self.target_candidate_count,
            'min_suitable_candidates': self.min_suitable_candidates,
            'source': self.source,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'additional_data': self.additional_data,
            'candidates_found': self.candidates_found,
            'candidates_suitable': self.candidates_suitable,
            'candidates_contacted': self.candidates_contacted,
            'candidates_responded': self.candidates_responded,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create project from dictionary."""
        return cls(
            id=ProjectId(data['id']),
            title=data['title'],
            company=data['company'],
            description=data['description'],
            requirements=data['requirements'],
            skills_needed=SkillSet(data.get('skills_needed', [])),
            location=data.get('location'),
            experience_required=data.get('experience_required'),
            stage=WorkflowStage(data['stage']),
            is_active=data.get('is_active', True),
            target_candidate_count=data.get('target_candidate_count', 50),
            min_suitable_candidates=data.get('min_suitable_candidates', 5),
            source=data.get('source'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            updated_at=datetime.fromisoformat(data['updated_at']) if isinstance(data.get('updated_at'), str) else data.get('updated_at', datetime.now()),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') and isinstance(data['completed_at'], str) else None,
            additional_data=data.get('additional_data', {}),
            candidates_found=data.get('candidates_found', 0),
            candidates_suitable=data.get('candidates_suitable', 0),
            candidates_contacted=data.get('candidates_contacted', 0),
            candidates_responded=data.get('candidates_responded', 0),
        )
    
    def __str__(self) -> str:
        return f"Project({self.title}, {self.company}, {self.stage.value})"
    
    def __repr__(self) -> str:
        return f"Project(id={self.id}, title='{self.title}', stage={self.stage.value})"
