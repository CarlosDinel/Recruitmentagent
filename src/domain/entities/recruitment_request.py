"""Recruitment Request Entity"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..value_objects import SkillSet


@dataclass
class RecruitmentRequest:
    """
    Recruitment Request entity representing an incoming recruitment request.
    This is the initial request that triggers the recruitment workflow.
    """
    
    # Identity
    id: str
    
    # Request Info
    position: str
    company: str
    description: str
    
    # Requirements
    required_skills: SkillSet
    
    # Request Source (required field, must come before optional fields)
    source: str  # 'frontend_user' or 'linkedin_api'
    
    # Optional fields (must come after required fields)
    location: Optional[str] = None
    experience_required: Optional[int] = None
    education_required: Optional[str] = None
    source_id: Optional[str] = None  # LinkedIn project ID if from API
    
    # User Information (if from frontend)
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    
    # Targets
    target_candidate_count: int = 50
    urgency: str = 'normal'  # 'low', 'normal', 'high', 'urgent'
    
    # Status
    status: str = 'pending'  # 'pending', 'processing', 'completed', 'failed'
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    
    # Result
    project_id: Optional[str] = None
    
    # Additional Data
    raw_request_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate request data."""
        if not self.position or not self.position.strip():
            raise ValueError("Position cannot be empty")
        
        if not self.company or not self.company.strip():
            raise ValueError("Company cannot be empty")
        
        if self.source not in ['frontend_user', 'linkedin_api']:
            raise ValueError(f"Invalid source: {self.source}")
        
        if self.urgency not in ['low', 'normal', 'high', 'urgent']:
            raise ValueError(f"Invalid urgency: {self.urgency}")
        
        if self.target_candidate_count < 1:
            raise ValueError("Target candidate count must be at least 1")
        
        if self.experience_required is not None and self.experience_required < 0:
            raise ValueError("Experience required cannot be negative")
    
    # Business Logic Methods
    
    def mark_processing(self) -> None:
        """Mark request as being processed."""
        if self.status != 'pending':
            raise ValueError(f"Cannot process request in status: {self.status}")
        
        self.status = 'processing'
        self.processed_at = datetime.now()
    
    def mark_completed(self, project_id: str) -> None:
        """Mark request as completed."""
        if self.status != 'processing':
            raise ValueError(f"Cannot complete request in status: {self.status}")
        
        self.status = 'completed'
        self.project_id = project_id
    
    def mark_failed(self) -> None:
        """Mark request as failed."""
        self.status = 'failed'
    
    def is_from_linkedin_api(self) -> bool:
        """Check if request came from LinkedIn API."""
        return self.source == 'linkedin_api'
    
    def is_from_frontend_user(self) -> bool:
        """Check if request came from frontend user."""
        return self.source == 'frontend_user'
    
    def is_urgent(self) -> bool:
        """Check if request is urgent."""
        return self.urgency in ['high', 'urgent']
    
    def get_priority_score(self) -> int:
        """Calculate priority score for request processing."""
        urgency_scores = {
            'low': 1,
            'normal': 2,
            'high': 3,
            'urgent': 4
        }
        return urgency_scores.get(self.urgency, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            'id': self.id,
            'position': self.position,
            'company': self.company,
            'description': self.description,
            'required_skills': self.required_skills.to_list(),
            'location': self.location,
            'experience_required': self.experience_required,
            'education_required': self.education_required,
            'source': self.source,
            'source_id': self.source_id,
            'requester_name': self.requester_name,
            'requester_email': self.requester_email,
            'target_candidate_count': self.target_candidate_count,
            'urgency': self.urgency,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'project_id': self.project_id,
            'raw_request_data': self.raw_request_data,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecruitmentRequest':
        """Create request from dictionary."""
        return cls(
            id=data['id'],
            position=data['position'],
            company=data['company'],
            description=data['description'],
            required_skills=SkillSet(data.get('required_skills', [])),
            location=data.get('location'),
            experience_required=data.get('experience_required'),
            education_required=data.get('education_required'),
            source=data['source'],
            source_id=data.get('source_id'),
            requester_name=data.get('requester_name'),
            requester_email=data.get('requester_email'),
            target_candidate_count=data.get('target_candidate_count', 50),
            urgency=data.get('urgency', 'normal'),
            status=data.get('status', 'pending'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            processed_at=datetime.fromisoformat(data['processed_at']) if data.get('processed_at') else None,
            project_id=data.get('project_id'),
            raw_request_data=data.get('raw_request_data', {}),
        )
    
    def __str__(self) -> str:
        return f"RecruitmentRequest({self.position}, {self.company}, {self.status})"
    
    def __repr__(self) -> str:
        return f"RecruitmentRequest(id={self.id}, position='{self.position}', status={self.status})"
