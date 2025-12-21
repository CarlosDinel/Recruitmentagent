"""
LangGraph Outreach Tools - Infrastructure Layer

This module contains LangGraph-compatible outreach tools decorated with @tool.
These tools are used by LangGraph agents for candidate outreach.

IMPORTANT: These tools MUST remain as @tool decorated for LangGraph compatibility.

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

from typing import Dict, Any, Optional
from langchain.tools import tool
import logging
from datetime import datetime

# Import infrastructure services
try:
    from ...infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
    from ...infrastructure.external_services.email.email_service_impl import EmailServiceImpl
except ImportError:
    LinkedInServiceImpl = None
    EmailServiceImpl = None

logger = logging.getLogger(__name__)


# Initialize services (singleton pattern)
_linkedin_service = None
_email_service = None


def _get_linkedin_service():
    """Get or create LinkedIn service instance."""
    global _linkedin_service
    if _linkedin_service is None and LinkedInServiceImpl:
        _linkedin_service = LinkedInServiceImpl()
    return _linkedin_service


def _get_email_service():
    """Get or create email service instance."""
    global _email_service
    if _email_service is None and EmailServiceImpl:
        _email_service = EmailServiceImpl()
    return _email_service


@tool
def linkedin_connection_request_tool(
    provider_id: str,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send LinkedIn connection request (LangGraph tool).
    
    Args:
        provider_id: LinkedIn user ID
        message: Optional personalized message
    
    Returns:
        Dict with status and confirmation details
    """
    try:
        logger.info(f"📤 Sending LinkedIn connection request to {provider_id}")
        
        linkedin_service = _get_linkedin_service()
        if linkedin_service:
            result = linkedin_service.send_connection_request(
                provider_id=provider_id,
                message=message
            )
            return {
                "action": "connection_request",
                "provider_id": provider_id,
                "status": "success",
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "confirmation": f"Connection request sent to {provider_id}"
            }
        else:
            # Fallback to old implementation
            from tools.outreach_tools import linkedin_connection_request
            return linkedin_connection_request.invoke({
                "provider_id": provider_id,
                "message": message
            })
            
    except Exception as e:
        logger.error(f"Error sending connection request: {e}")
        return {
            "action": "connection_request",
            "status": "error",
            "error": str(e)
        }


@tool
def linkedin_message_send_tool(
    provider_id: str,
    message: str
) -> Dict[str, Any]:
    """
    Send LinkedIn direct message (LangGraph tool).
    
    Args:
        provider_id: LinkedIn user ID
        message: Message text to send
    
    Returns:
        Dict with status and confirmation details
    """
    try:
        logger.info(f"💬 Sending LinkedIn message to {provider_id}")
        
        linkedin_service = _get_linkedin_service()
        if linkedin_service:
            result = linkedin_service.send_message(
                provider_id=provider_id,
                message=message
            )
            return {
                "action": "linkedin_message",
                "provider_id": provider_id,
                "status": "success",
                "message_length": len(message),
                "timestamp": datetime.now().isoformat(),
                "confirmation": f"Message sent to {provider_id}"
            }
        else:
            # Fallback to old implementation
            from tools.outreach_tools import linkedin_message_send
            return linkedin_message_send.invoke({
                "provider_id": provider_id,
                "message": message
            })
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return {
            "action": "linkedin_message",
            "status": "error",
            "error": str(e)
        }


@tool
def linkedin_inmail_send_tool(
    provider_id: str,
    subject: str,
    body: str
) -> Dict[str, Any]:
    """
    Send LinkedIn InMail (LangGraph tool).
    
    Args:
        provider_id: LinkedIn user ID
        subject: InMail subject line
        body: InMail message body
    
    Returns:
        Dict with status and confirmation details
    """
    try:
        logger.info(f"📧 Sending LinkedIn InMail to {provider_id}")
        
        linkedin_service = _get_linkedin_service()
        if linkedin_service:
            result = linkedin_service.send_inmail(
                provider_id=provider_id,
                subject=subject,
                body=body
            )
            return {
                "action": "inmail",
                "provider_id": provider_id,
                "status": "success",
                "subject": subject,
                "body_length": len(body),
                "timestamp": datetime.now().isoformat(),
                "confirmation": f"InMail sent to {provider_id}"
            }
        else:
            # Fallback to old implementation
            from tools.outreach_tools import linkedin_inmail_send
            return linkedin_inmail_send.invoke({
                "provider_id": provider_id,
                "subject": subject,
                "body": body
            })
            
    except Exception as e:
        logger.error(f"Error sending InMail: {e}")
        return {
            "action": "inmail",
            "status": "error",
            "error": str(e)
        }


@tool
def send_outreach_email_tool(
    recipient_email: str,
    subject: str,
    body: str
) -> Dict[str, Any]:
    """
    Send outreach email (LangGraph tool).
    
    Args:
        recipient_email: Email address of recipient
        subject: Email subject line
        body: Email message body
    
    Returns:
        Dict with status and confirmation details
    """
    try:
        logger.info(f"📧 Sending email to {recipient_email}")
        
        email_service = _get_email_service()
        if email_service:
            result = email_service.send_email(
                to_email=recipient_email,
                subject=subject,
                body=body
            )
            return {
                "action": "email_sent",
                "recipient_email": recipient_email,
                "status": "success",
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
                "confirmation": f"Email sent to {recipient_email}"
            }
        else:
            # Fallback to old implementation
            from tools.outreach_tools import send_outreach_email
            return send_outreach_email.invoke({
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body
            })
            
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            "action": "email_sent",
            "status": "error",
            "error": str(e)
        }

