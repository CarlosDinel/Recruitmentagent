"""Outreach Channel Enum"""

from enum import Enum


class OutreachChannel(str, Enum):
    """Communication channels for candidate outreach."""
    
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    
    def is_digital(self) -> bool:
        """Check if channel is digital."""
        return self in [self.EMAIL, self.LINKEDIN]
    
    def requires_phone_number(self) -> bool:
        """Check if channel requires phone number."""
        return self in [self.PHONE, self.SMS, self.WHATSAPP]
    
    def supports_attachments(self) -> bool:
        """Check if channel supports file attachments."""
        return self in [self.EMAIL, self.LINKEDIN]
