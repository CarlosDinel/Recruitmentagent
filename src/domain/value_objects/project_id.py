"""Project ID Value Object"""

from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass(frozen=True)
class ProjectId:
    """Immutable unique identifier for a recruitment project."""
    
    value: str
    
    def __post_init__(self):
        """Validate the project ID."""
        if not self.value:
            raise ValueError("Project ID cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Project ID too long (max 100 characters)")
    
    @classmethod
    def generate(cls, prefix: str = "REQ") -> 'ProjectId':
        """Generate a new recruitment project ID."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        unique = uuid.uuid4().hex[:6].upper()
        return cls(value=f"{prefix}-{timestamp}-{unique}")
    
    @classmethod
    def from_linkedin_project(cls, linkedin_project_id: str) -> 'ProjectId':
        """Create project ID from LinkedIn API project ID."""
        if not linkedin_project_id:
            raise ValueError("LinkedIn project ID cannot be empty")
        return cls(value=f"LI-{linkedin_project_id}")
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"ProjectId('{self.value}')"
