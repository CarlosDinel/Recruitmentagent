"""SMTP client for sending emails."""

import os
import smtplib
import logging
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SMTPClient:
    """SMTP client for sending emails."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True
    ):
        """
        Initialize SMTP client.
        
        Args:
            host: SMTP server host (defaults to EMAIL_HOST env var)
            port: SMTP server port (defaults to EMAIL_PORT env var)
            username: SMTP username (defaults to EMAIL_USERNAME env var)
            password: SMTP password (defaults to EMAIL_PASSWORD env var)
            use_tls: Whether to use TLS encryption
        """
        self.host = host or os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        self.port = port or int(os.getenv('EMAIL_PORT', '587'))
        self.username = username or os.getenv('EMAIL_USERNAME')
        self.password = password or os.getenv('EMAIL_PASSWORD')
        self.use_tls = use_tls
        
        if not self.username:
            raise ValueError("EMAIL_USERNAME is required")
        if not self.password:
            raise ValueError("EMAIL_PASSWORD is required")
        
        logger.info(f"SMTPClient initialized for {self.host}:{self.port}")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        is_html: bool = False
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            from_email: Sender email (defaults to EMAIL_USERNAME)
            cc: CC recipients
            bcc: BCC recipients
            is_html: Whether body is HTML
            
        Returns:
            True if email sent successfully
            
        Raises:
            smtplib.SMTPException: If email sending fails
        """
        try:
            from_email = from_email or self.username
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Connect and send
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                
                server.send_message(msg, to_addrs=recipients)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            raise
    
    def send_bulk_emails(
        self,
        emails: List[dict],
        from_email: Optional[str] = None
    ) -> List[dict]:
        """
        Send multiple emails in bulk.
        
        Args:
            emails: List of email dicts with keys: to_email, subject, body
            from_email: Sender email
            
        Returns:
            List of results with status for each email
        """
        results = []
        
        for email_data in emails:
            try:
                success = self.send_email(
                    to_email=email_data['to_email'],
                    subject=email_data['subject'],
                    body=email_data['body'],
                    from_email=from_email,
                    is_html=email_data.get('is_html', False)
                )
                results.append({
                    'to_email': email_data['to_email'],
                    'status': 'success' if success else 'failed'
                })
            except Exception as e:
                results.append({
                    'to_email': email_data['to_email'],
                    'status': 'error',
                    'error': str(e)
                })
        
        logger.info(f"Bulk email send completed: {len([r for r in results if r['status'] == 'success'])}/{len(emails)} successful")
        return results

