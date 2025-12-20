"""Candidate Entity - Core Business Object"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..value_objects import CandidateId, SkillSet, ContactInfo, EvaluationScore
from ..enums import CandidateStatus


@dataclass
class Candidate:
    """
    Candidate entity representing a recruitment candidate.
    This is a rich domain model with business logic.
    """
    
    # Identity
    id: CandidateId
    
    # Basic Info
    name: str
    current_position: Optional[str]
    current_company: Optional[str]
    location: Optional[str]
    
    # Contact
    contact_info: ContactInfo
    
    # Professional Info
    skills: SkillSet
    years_experience: Optional[int]
    education: Optional[str]
    
    # Status
    status: CandidateStatus
    
    # Evaluation
    evaluation_score: Optional[EvaluationScore] = None
    
    # Profile Data
    profile_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    source: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Project Association
    project_id: Optional[str] = None
    campaign_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate candidate data."""
        if not self.name or not self.name.strip():
            raise ValueError("Candidate name cannot be empty")
        
        if self.years_experience is not None and self.years_experience < 0:
            raise ValueError("Years of experience cannot be negative")
    
    # Business Logic Methods
    
    def evaluate(self, score: EvaluationScore) -> None:
        """Evaluate the candidate and update status."""
        self.evaluation_score = score
        new_status = score.to_evaluation_result().to_candidate_status()
        self.update_status(new_status)
    
    def update_status(self, new_status: CandidateStatus) -> None:
        """Update candidate status with validation."""
        # Validate status transitions
        if not self._is_valid_status_transition(self.status, new_status):
            raise ValueError(f"Invalid status transition from {self.status} to {new_status}")
        
        self.status = new_status
        self.updated_at = datetime.now()
    
    def enrich_profile(self, profile_data: Dict[str, Any]) -> None:
        """Enrich candidate profile with additional data."""
        self.profile_data.update(profile_data)
        
        # Update status if currently enriching
        if self.status == CandidateStatus.ENRICHING:
            self.update_status(CandidateStatus.ENRICHED)
        
        self.updated_at = datetime.now()
    
    def mark_contacted(self, channel: str) -> None:
        """Mark candidate as contacted."""
        if not self.contact_info.supports_channel(channel):
            raise ValueError(f"Contact info does not support channel: {channel}")
        
        self.update_status(CandidateStatus.CONTACTED)
    
    def mark_responded(self) -> None:
        """Mark candidate as responded."""
        if self.status != CandidateStatus.CONTACTED:
            raise ValueError("Can only mark responded if candidate was contacted")
        
        self.update_status(CandidateStatus.RESPONDED)
    
    def is_suitable_for_outreach(self) -> bool:
        """Check if candidate is suitable for outreach."""
        return self.status.is_suitable_for_outreach()
    
    def is_active(self) -> bool:
        """Check if candidate is still active in pipeline."""
        return self.status.is_active()
    
    def matches_skills(self, required_skills: List[str], min_match: float = 0.5) -> bool:
        """Check if candidate matches required skills."""
        required_skill_set = SkillSet(required_skills)
        match_score = self.skills.match_score(required_skill_set)
        return match_score >= min_match
    
    @staticmethod
    def _is_valid_status_transition(current: CandidateStatus, new: CandidateStatus) -> bool:
        """Validate status transitions."""
        # Terminal states cannot transition
        if not current.is_active():
            return False
        
        # Define allowed transitions
        allowed_transitions = {
            CandidateStatus.NEW: [CandidateStatus.IDENTIFIED, CandidateStatus.EVALUATING],
            CandidateStatus.IDENTIFIED: [CandidateStatus.EVALUATING],
            CandidateStatus.EVALUATING: [
                CandidateStatus.SUITABLE,
                CandidateStatus.MAYBE,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.SUITABLE: [
                CandidateStatus.ENRICHING,
                CandidateStatus.PRIORITIZED,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.MAYBE: [
                CandidateStatus.ENRICHING,
                CandidateStatus.SUITABLE,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.ENRICHING: [
                CandidateStatus.ENRICHED,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.ENRICHED: [
                CandidateStatus.PRIORITIZED,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.PRIORITIZED: [
                CandidateStatus.OUTREACH_PENDING,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.OUTREACH_PENDING: [
                CandidateStatus.CONTACTED,
                CandidateStatus.UNSUITABLE
            ],
            CandidateStatus.CONTACTED: [
                CandidateStatus.RESPONDED,
                CandidateStatus.NOT_RESPONDED,
                CandidateStatus.INTERVIEW_SCHEDULED
            ],
            CandidateStatus.RESPONDED: [
                CandidateStatus.INTERVIEW_SCHEDULED,
                CandidateStatus.REJECTED
            ],
            CandidateStatus.INTERVIEW_SCHEDULED: [
                CandidateStatus.INTERVIEWED,
                CandidateStatus.WITHDRAWN
            ],
            CandidateStatus.INTERVIEWED: [
                CandidateStatus.OFFERED,
                CandidateStatus.REJECTED
            ],
            CandidateStatus.OFFERED: [
                CandidateStatus.HIRED,
                CandidateStatus.DECLINED
            ],
        }
        
        return new in allowed_transitions.get(current, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            'id': str(self.id),
            'name': self.name,
            'current_position': self.current_position,
            'current_company': self.current_company,
            'location': self.location,
            'contact_info': {
                'email': self.contact_info.email,
                'phone': self.contact_info.phone,
                'linkedin_url': self.contact_info.linkedin_url,
            },
            'skills': self.skills.to_list(),
            'years_experience': self.years_experience,
            'education': self.education,
            'status': self.status.value,
            'evaluation_score': self.evaluation_score.to_dict() if self.evaluation_score else None,
            'profile_data': self.profile_data,
            'source': self.source,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'project_id': self.project_id,
            'campaign_id': self.campaign_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Candidate':
        """Create candidate from dictionary."""
        contact_info_data = data.get('contact_info', {})
        
        evaluation_score = None
        if data.get('evaluation_score'):
            eval_data = data['evaluation_score']
            evaluation_score = EvaluationScore(
                overall_score=eval_data['overall_score'],
                skill_match_score=eval_data['skill_match_score'],
                experience_score=eval_data['experience_score'],
                culture_fit_score=eval_data.get('culture_fit_score'),
                reasoning=eval_data['reasoning']
            )
        
        return cls(
            id=CandidateId(data['id']),
            name=data['name'],
            current_position=data.get('current_position'),
            current_company=data.get('current_company'),
            location=data.get('location'),
            contact_info=ContactInfo(
                email=contact_info_data.get('email'),
                phone=contact_info_data.get('phone'),
                linkedin_url=contact_info_data.get('linkedin_url')
            ),
            skills=SkillSet(data.get('skills', [])),
            years_experience=data.get('years_experience'),
            education=data.get('education'),
            status=CandidateStatus(data['status']),
            evaluation_score=evaluation_score,
            profile_data=data.get('profile_data', {}),
            source=data.get('source'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            updated_at=datetime.fromisoformat(data['updated_at']) if isinstance(data.get('updated_at'), str) else data.get('updated_at', datetime.now()),
            project_id=data.get('project_id'),
            campaign_id=data.get('campaign_id'),
        )
    
    def __str__(self) -> str:
        return f"Candidate({self.name}, {self.status.value})"
    
    def __repr__(self) -> str:
        return f"Candidate(id={self.id}, name='{self.name}', status={self.status.value})"
