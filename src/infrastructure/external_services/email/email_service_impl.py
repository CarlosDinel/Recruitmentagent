"""Email Service Implementation."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .smtp_client import SMTPClient

logger = logging.getLogger(__name__)


class EmailServiceImpl:
    """Implementation of email service using SMTP."""
    
    def __init__(self, smtp_client: Optional[SMTPClient] = None):
        """
        Initialize email service.
        
        Args:
            smtp_client: Optional SMTP client (creates default if not provided)
        """
        self.smtp_client = smtp_client or SMTPClient()
        logger.info("EmailServiceImpl initialized")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            from_email: Sender email
            cc: CC recipients
            bcc: BCC recipients
            is_html: Whether body is HTML
            
        Returns:
            Result dictionary with status
        """
        try:
            success = self.smtp_client.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                from_email=from_email,
                cc=cc,
                bcc=bcc,
                is_html=is_html
            )
            
            return {
                "status": "success" if success else "failed",
                "recipient_email": to_email,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return {
                "status": "error",
                "recipient_email": to_email,
                "error": str(e)
            }
    
    def send_bulk_emails(
        self,
        emails: List[dict],
        from_email: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails in bulk.
        
        Args:
            emails: List of email dicts with keys: to_email, subject, body
            from_email: Sender email
            
        Returns:
            List of results with status for each email
        """
        return self.smtp_client.send_bulk_emails(emails, from_email)

