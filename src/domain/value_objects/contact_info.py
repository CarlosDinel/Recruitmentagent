"""Contact Info Value Object"""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass(frozen=True)
class ContactInfo:
    """Immutable contact information for a candidate."""
    
    email: Optional[str]
    phone: Optional[str]
    linkedin_url: Optional[str]
    
    def __post_init__(self):
        """Validate contact information."""
        if self.email:
            self._validate_email(self.email)
        if self.phone:
            self._validate_phone(self.phone)
        if self.linkedin_url:
            self._validate_linkedin_url(self.linkedin_url)
        
        # At least one contact method must be provided
        if not any([self.email, self.phone, self.linkedin_url]):
            raise ValueError("At least one contact method must be provided")
    
    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError(f"Invalid email format: {email}")
    
    @staticmethod
    def _validate_phone(phone: str) -> None:
        """Validate phone number format."""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)]+', '', phone)
        # Check if it contains only digits and + sign
        if not re.match(r'^\+?[0-9]{8,15}$', cleaned):
            raise ValueError(f"Invalid phone format: {phone}")
    
    @staticmethod
    def _validate_linkedin_url(url: str) -> None:
        """Validate LinkedIn URL format."""
        if not url.startswith(('https://linkedin.com/', 'https://www.linkedin.com/', 
                               'http://linkedin.com/', 'http://www.linkedin.com/')):
            raise ValueError(f"Invalid LinkedIn URL: {url}")
    
    def has_email(self) -> bool:
        """Check if email is available."""
        return self.email is not None
    
    def has_phone(self) -> bool:
        """Check if phone is available."""
        return self.phone is not None
    
    def has_linkedin(self) -> bool:
        """Check if LinkedIn URL is available."""
        return self.linkedin_url is not None
    
    def supports_channel(self, channel: str) -> bool:
        """Check if contact info supports a specific outreach channel."""
        from ..enums import OutreachChannel
        
        channel_enum = OutreachChannel(channel) if isinstance(channel, str) else channel
        
        if channel_enum == OutreachChannel.EMAIL:
            return self.has_email()
        elif channel_enum == OutreachChannel.LINKEDIN:
            return self.has_linkedin()
        elif channel_enum in [OutreachChannel.PHONE, OutreachChannel.SMS, OutreachChannel.WHATSAPP]:
            return self.has_phone()
        
        return False
    
    def __str__(self) -> str:
        parts = []
        if self.email:
            parts.append(f"email={self.email}")
        if self.phone:
            parts.append(f"phone={self.phone}")
        if self.linkedin_url:
            parts.append(f"linkedin={self.linkedin_url}")
        return f"ContactInfo({', '.join(parts)})"
