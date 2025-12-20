"""Outreach Message Entity"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

from ..value_objects import CandidateId
from ..enums import OutreachChannel


@dataclass
class OutreachMessage:
    """
    Outreach Message entity representing a message sent to a candidate.
    """
    
    # Identity
    id: str
    candidate_id: CandidateId
    campaign_id: str
    
    # Message Content
    subject: Optional[str]
    body: str
    channel: OutreachChannel
    
    # Status
    status: str  # 'draft', 'sent', 'delivered', 'failed', 'responded'
    
    # Response
    response_text: Optional[str] = None
    response_received_at: Optional[datetime] = None
    is_positive_response: Optional[bool] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Additional Data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate message data."""
        if not self.id:
            raise ValueError("Message ID cannot be empty")
        
        if not self.body or not self.body.strip():
            raise ValueError("Message body cannot be empty")
        
        if self.channel == OutreachChannel.EMAIL and not self.subject:
            raise ValueError("Email messages must have a subject")
    
    # Business Logic Methods
    
    def mark_sent(self) -> None:
        """Mark message as sent."""
        if self.status != 'draft':
            raise ValueError(f"Cannot mark message as sent from status: {self.status}")
        
        self.status = 'sent'
        self.sent_at = datetime.now()
    
    def mark_delivered(self) -> None:
        """Mark message as delivered."""
        if self.status != 'sent':
            raise ValueError(f"Cannot mark message as delivered from status: {self.status}")
        
        self.status = 'delivered'
        self.delivered_at = datetime.now()
    
    def mark_failed(self) -> None:
        """Mark message as failed."""
        self.status = 'failed'
    
    def record_response(self, response_text: str, is_positive: bool = False) -> None:
        """Record a response to the message."""
        if self.status not in ['sent', 'delivered']:
            raise ValueError(f"Cannot record response for message in status: {self.status}")
        
        self.status = 'responded'
        self.response_text = response_text
        self.response_received_at = datetime.now()
        self.is_positive_response = is_positive
    
    def is_sent(self) -> bool:
        """Check if message was sent."""
        return self.status in ['sent', 'delivered', 'responded']
    
    def is_delivered(self) -> bool:
        """Check if message was delivered."""
        return self.status in ['delivered', 'responded']
    
    def has_response(self) -> bool:
        """Check if candidate responded."""
        return self.status == 'responded'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            'id': self.id,
            'candidate_id': str(self.candidate_id),
            'campaign_id': self.campaign_id,
            'subject': self.subject,
            'body': self.body,
            'channel': self.channel.value,
            'status': self.status,
            'response_text': self.response_text,
            'response_received_at': self.response_received_at.isoformat() if self.response_received_at else None,
            'is_positive_response': self.is_positive_response,
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OutreachMessage':
        """Create message from dictionary."""
        return cls(
            id=data['id'],
            candidate_id=CandidateId(data['candidate_id']),
            campaign_id=data['campaign_id'],
            subject=data.get('subject'),
            body=data['body'],
            channel=OutreachChannel(data['channel']),
            status=data['status'],
            response_text=data.get('response_text'),
            response_received_at=datetime.fromisoformat(data['response_received_at']) if data.get('response_received_at') else None,
            is_positive_response=data.get('is_positive_response'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            sent_at=datetime.fromisoformat(data['sent_at']) if data.get('sent_at') else None,
            delivered_at=datetime.fromisoformat(data['delivered_at']) if data.get('delivered_at') else None,
            metadata=data.get('metadata', {}),
        )
    
    def __str__(self) -> str:
        return f"OutreachMessage({self.channel.value}, {self.status})"
    
    def __repr__(self) -> str:
        return f"OutreachMessage(id={self.id}, channel={self.channel.value}, status={self.status})"
