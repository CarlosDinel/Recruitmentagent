"""Candidate ID Value Object"""

from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass(frozen=True)
class CandidateId:
    """Immutable unique identifier for a candidate."""
    
    value: str
    
    def __post_init__(self):
        """Validate the candidate ID."""
        if not self.value:
            raise ValueError("Candidate ID cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Candidate ID too long (max 100 characters)")
    
    @classmethod
    def generate(cls) -> 'CandidateId':
        """Generate a new random candidate ID."""
        return cls(value=f"CAND-{uuid.uuid4().hex[:12].upper()}")
    
    @classmethod
    def from_linkedin_url(cls, linkedin_url: str) -> 'CandidateId':
        """Create candidate ID from LinkedIn URL (for deduplication)."""
        if not linkedin_url:
            raise ValueError("LinkedIn URL cannot be empty")
        
        # Extract username from LinkedIn URL
        # Examples: 
        # https://www.linkedin.com/in/john-doe/ -> john-doe
        # https://linkedin.com/in/john-doe -> john-doe
        parts = linkedin_url.rstrip('/').split('/')
        username = parts[-1] if parts else linkedin_url
        
        return cls(value=f"CAND-LI-{username.upper()}")
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"CandidateId('{self.value}')"
