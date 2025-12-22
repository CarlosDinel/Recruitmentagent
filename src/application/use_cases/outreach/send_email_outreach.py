"""
Send Email Outreach Use Case - Clean Architecture

This use case sends email outreach messages to candidates.
It follows Clean Architecture principles by using domain entities and services.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ....domain.entities.candidate import Candidate
from ....domain.entities.project import Project
from ....domain.enums.candidate_status import CandidateStatus
from ....domain.repositories.candidate_repository import CandidateRepository

# Infrastructure services (injected)
try:
    from ....infrastructure.external_services.email.email_service_impl import EmailServiceImpl
except ImportError:
    EmailServiceImpl = None

logger = logging.getLogger(__name__)


class SendEmailOutreachRequest:
    """Request DTO for sending email outreach."""
    
    def __init__(
        self,
        candidate: Candidate,
        project: Project,
        subject: Optional[str] = None,
        message_template: Optional[str] = None,
        personalization_data: Optional[Dict[str, Any]] = None
    ):
        self.candidate = candidate
        self.project = project
        self.subject = subject
        self.message_template = message_template
        self.personalization_data = personalization_data or {}


class SendEmailOutreachResponse:
    """Response DTO for email outreach."""
    
    def __init__(
        self,
        success: bool,
        candidate: Candidate,
        email_sent: bool,
        delivery_status: str,
        message_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.candidate = candidate
        self.email_sent = email_sent
        self.delivery_status = delivery_status
        self.message_id = message_id
        self.error = error
        self.metadata = metadata or {}


class SendEmailOutreachUseCase:
    """
    Use case for sending email outreach messages to candidates.
    
    This use case sends personalized email messages to candidates. It follows
    Clean Architecture by using infrastructure services through interfaces.
    
    Example:
        >>> use_case = SendEmailOutreachUseCase(
        ...     candidate_repository=candidate_repo,
        ...     email_service=email_service
        ... )
        >>> 
        >>> request = SendEmailOutreachRequest(
        ...     candidate=candidate,
        ...     project=project,
        ...     subject="Career Opportunity"
        ... )
        >>> 
        >>> response = await use_case.execute(request)
        >>> print(f"Email sent: {response.email_sent}")
    """
    
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        email_service: Optional[EmailServiceImpl] = None
    ):
        """
        Initialize send email outreach use case.
        
        Args:
            candidate_repository: Repository for candidate persistence
            email_service: Optional email service for sending emails
        """
        self.candidate_repository = candidate_repository
        self.email_service = email_service
        logger.info("SendEmailOutreachUseCase initialized")
    
    async def execute(self, request: SendEmailOutreachRequest) -> SendEmailOutreachResponse:
        """
        Execute email outreach.
        
        Args:
            request: Email outreach request with candidate and project
        
        Returns:
            Email outreach response with delivery status
        """
        logger.info(f"Sending email outreach to {request.candidate.name}")
        
        try:
            # Validate candidate has email
            email = request.candidate.contact_info.email
            if not email:
                return SendEmailOutreachResponse(
                    success=False,
                    candidate=request.candidate,
                    email_sent=False,
                    delivery_status="failed",
                    error="Candidate has no email address"
                )
            
            # Generate message if template provided
            message_body = request.message_template or self._generate_default_message(
                candidate=request.candidate,
                project=request.project,
                personalization_data=request.personalization_data
            )
            
            # Generate subject if not provided
            subject = request.subject or f"Opportunity: {request.project.title} at {request.project.company}"
            
            # Send email via service
            email_sent = False
            delivery_status = "pending"
            message_id = None
            error = None
            
            if self.email_service:
                try:
                    result = self.email_service.send_email(
                        to_email=email,
                        subject=subject,
                        body=message_body
                    )
                    email_sent = result.get('success', False)
                    delivery_status = "sent" if email_sent else "failed"
                    message_id = result.get('message_id')
                    error = result.get('error')
                except Exception as e:
                    logger.error(f"Error sending email: {e}")
                    email_sent = False
                    delivery_status = "failed"
                    error = str(e)
            else:
                logger.warning("Email service not available, using mock")
                email_sent = True
                delivery_status = "sent_mock"
            
            # Update candidate status if email sent successfully
            if email_sent:
                try:
                    request.candidate.mark_contacted("email")
                    await self.candidate_repository.save(request.candidate)
                except Exception as e:
                    logger.warning(f"Error updating candidate status: {e}")
            
            metadata = {
                "sent_at": datetime.now().isoformat(),
                "subject": subject,
                "email_address": email,
                "project_id": str(request.project.id)
            }
            
            return SendEmailOutreachResponse(
                success=email_sent,
                candidate=request.candidate,
                email_sent=email_sent,
                delivery_status=delivery_status,
                message_id=message_id,
                error=error,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error executing email outreach: {e}")
            return SendEmailOutreachResponse(
                success=False,
                candidate=request.candidate,
                email_sent=False,
                delivery_status="error",
                error=str(e)
            )
    
    def _generate_default_message(
        self,
        candidate: Candidate,
        project: Project,
        personalization_data: Dict[str, Any]
    ) -> str:
        """Generate default email message."""
        skills_mention = ", ".join(list(candidate.skills.skills)[:3]) if candidate.skills.skills else "your background"
        
        message = f"""Hi {candidate.name},

I hope this message finds you well. I'm reaching out about a {project.title} opportunity at {project.company}.

Based on your background in {skills_mention}, I thought you might be interested in this role.

{project.description[:200]}...

Would you be open to a brief conversation to discuss this opportunity?

Best regards,
Recruitment Team"""
        
        return message

