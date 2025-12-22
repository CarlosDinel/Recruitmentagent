"""Campaign Entity - Outreach Campaign"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..value_objects import ProjectId
from ..enums import OutreachChannel


@dataclass
class Campaign:
    """
    Campaign entity representing an outreach campaign.
    Multiple campaigns can belong to one project.
    """
    
    # Identity
    id: str
    project_id: ProjectId
    
    # Basic Info
    name: str
    channel: OutreachChannel
    
    # Status
    is_active: bool = True
    
    # Targets
    target_candidates: List[str] = field(default_factory=list)
    
    # Metrics
    messages_sent: int = 0
    messages_delivered: int = 0
    responses_received: int = 0
    positive_responses: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Additional Data
    campaign_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate campaign data."""
        if not self.name or not self.name.strip():
            raise ValueError("Campaign name cannot be empty")
        
        if not self.id:
            raise ValueError("Campaign ID cannot be empty")
    
    # Business Logic Methods
    
    def add_candidate(self, candidate_id: str) -> None:
        """Add candidate to campaign."""
        if candidate_id not in self.target_candidates:
            self.target_candidates.append(candidate_id)
            self.updated_at = datetime.now()
    
    def record_message_sent(self, delivered: bool = True) -> None:
        """Record that a message was sent."""
        self.messages_sent += 1
        if delivered:
            self.messages_delivered += 1
        self.updated_at = datetime.now()
    
    def record_response(self, is_positive: bool = False) -> None:
        """Record a response from a candidate."""
        self.responses_received += 1
        if is_positive:
            self.positive_responses += 1
        self.updated_at = datetime.now()
    
    def calculate_delivery_rate(self) -> float:
        """Calculate message delivery rate."""
        if self.messages_sent == 0:
            return 0.0
        return self.messages_delivered / self.messages_sent
    
    def calculate_response_rate(self) -> float:
        """Calculate response rate."""
        if self.messages_delivered == 0:
            return 0.0
        return self.responses_received / self.messages_delivered
    
    def calculate_conversion_rate(self) -> float:
        """Calculate positive response conversion rate."""
        if self.responses_received == 0:
            return 0.0
        return self.positive_responses / self.responses_received
    
    def complete_campaign(self) -> None:
        """Mark campaign as completed."""
        self.is_active = False
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            'id': self.id,
            'project_id': str(self.project_id),
            'name': self.name,
            'channel': self.channel.value,
            'is_active': self.is_active,
            'target_candidates': self.target_candidates,
            'messages_sent': self.messages_sent,
            'messages_delivered': self.messages_delivered,
            'responses_received': self.responses_received,
            'positive_responses': self.positive_responses,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'campaign_config': self.campaign_config,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Campaign':
        """Create campaign from dictionary."""
        return cls(
            id=data['id'],
            project_id=ProjectId(data['project_id']),
            name=data['name'],
            channel=OutreachChannel(data['channel']),
            is_active=data.get('is_active', True),
            target_candidates=data.get('target_candidates', []),
            messages_sent=data.get('messages_sent', 0),
            messages_delivered=data.get('messages_delivered', 0),
            responses_received=data.get('responses_received', 0),
            positive_responses=data.get('positive_responses', 0),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            updated_at=datetime.fromisoformat(data['updated_at']) if isinstance(data.get('updated_at'), str) else data.get('updated_at', datetime.now()),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') and isinstance(data['completed_at'], str) else None,
            campaign_config=data.get('campaign_config', {}),
        )
    
    def __str__(self) -> str:
        return f"Campaign({self.name}, {self.channel.value})"
    
    def __repr__(self) -> str:
        return f"Campaign(id={self.id}, name='{self.name}', channel={self.channel.value})"
