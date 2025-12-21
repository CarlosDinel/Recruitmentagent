"""
Send LinkedIn Outreach Use Case - Clean Architecture

This use case sends LinkedIn outreach messages (connection requests, messages, InMail).
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
    from ....infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
except ImportError:
    LinkedInServiceImpl = None

logger = logging.getLogger(__name__)


class SendLinkedInOutreachRequest:
    """Request DTO for sending LinkedIn outreach."""
    
    def __init__(
        self,
        candidate: Candidate,
        project: Project,
        outreach_type: str = "message",  # "connection", "message", "inmail"
        message: Optional[str] = None,
        personalization_data: Optional[Dict[str, Any]] = None
    ):
        self.candidate = candidate
        self.project = project
        self.outreach_type = outreach_type
        self.message = message
        self.personalization_data = personalization_data or {}


class SendLinkedInOutreachResponse:
    """Response DTO for LinkedIn outreach."""
    
    def __init__(
        self,
        success: bool,
        candidate: Candidate,
        outreach_sent: bool,
        outreach_type: str,
        delivery_status: str,
        message_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.candidate = candidate
        self.outreach_sent = outreach_sent
        self.outreach_type = outreach_type
        self.delivery_status = delivery_status
        self.message_id = message_id
        self.error = error
        self.metadata = metadata or {}


class SendLinkedInOutreachUseCase:
    """
    Use case for sending LinkedIn outreach messages to candidates.
    
    This use case sends LinkedIn connection requests, messages, or InMails to candidates.
    It follows Clean Architecture by using infrastructure services through interfaces.
    
    Example:
        >>> use_case = SendLinkedInOutreachUseCase(
        ...     candidate_repository=candidate_repo,
        ...     linkedin_service=linkedin_service
        ... )
        >>> 
        >>> request = SendLinkedInOutreachRequest(
        ...     candidate=candidate,
        ...     project=project,
        ...     outreach_type="message"
        ... )
        >>> 
        >>> response = await use_case.execute(request)
        >>> print(f"Outreach sent: {response.outreach_sent}")
    """
    
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        linkedin_service: Optional[LinkedInServiceImpl] = None
    ):
        """
        Initialize send LinkedIn outreach use case.
        
        Args:
            candidate_repository: Repository for candidate persistence
            linkedin_service: Optional LinkedIn service for sending outreach
        """
        self.candidate_repository = candidate_repository
        self.linkedin_service = linkedin_service
        logger.info("SendLinkedInOutreachUseCase initialized")
    
    async def execute(self, request: SendLinkedInOutreachRequest) -> SendLinkedInOutreachResponse:
        """
        Execute LinkedIn outreach.
        
        Args:
            request: LinkedIn outreach request with candidate and project
        
        Returns:
            LinkedIn outreach response with delivery status
        """
        logger.info(f"Sending LinkedIn {request.outreach_type} to {request.candidate.name}")
        
        try:
            # Validate candidate has LinkedIn URL
            linkedin_url = request.candidate.contact_info.linkedin_url
            if not linkedin_url:
                return SendLinkedInOutreachResponse(
                    success=False,
                    candidate=request.candidate,
                    outreach_sent=False,
                    outreach_type=request.outreach_type,
                    delivery_status="failed",
                    error="Candidate has no LinkedIn URL"
                )
            
            # Extract LinkedIn ID from URL
            linkedin_id = self._extract_linkedin_id(linkedin_url)
            if not linkedin_id:
                return SendLinkedInOutreachResponse(
                    success=False,
                    candidate=request.candidate,
                    outreach_sent=False,
                    outreach_type=request.outreach_type,
                    delivery_status="failed",
                    error="Could not extract LinkedIn ID from URL"
                )
            
            # Generate message if not provided
            message = request.message or self._generate_default_message(
                candidate=request.candidate,
                project=request.project,
                personalization_data=request.personalization_data
            )
            
            # Send outreach via service
            outreach_sent = False
            delivery_status = "pending"
            message_id = None
            error = None
            
            if self.linkedin_service:
                try:
                    if request.outreach_type == "connection":
                        result = self.linkedin_service.send_connection_request(
                            provider_id=linkedin_id,
                            message=message
                        )
                    elif request.outreach_type == "inmail":
                        result = self.linkedin_service.send_inmail(
                            provider_id=linkedin_id,
                            subject=f"Opportunity: {request.project.title}",
                            body=message
                        )
                    else:  # message
                        result = self.linkedin_service.send_message(
                            provider_id=linkedin_id,
                            message=message
                        )
                    
                    outreach_sent = result.get('success', False)
                    delivery_status = "sent" if outreach_sent else "failed"
                    message_id = result.get('message_id')
                    error = result.get('error')
                    
                except Exception as e:
                    logger.error(f"Error sending LinkedIn outreach: {e}")
                    outreach_sent = False
                    delivery_status = "failed"
                    error = str(e)
            else:
                logger.warning("LinkedIn service not available, using mock")
                outreach_sent = True
                delivery_status = "sent_mock"
            
            # Update candidate status if outreach sent successfully
            if outreach_sent:
                try:
                    request.candidate.mark_contacted("linkedin")
                    await self.candidate_repository.save(request.candidate)
                except Exception as e:
                    logger.warning(f"Error updating candidate status: {e}")
            
            metadata = {
                "sent_at": datetime.now().isoformat(),
                "linkedin_id": linkedin_id,
                "linkedin_url": linkedin_url,
                "project_id": str(request.project.id)
            }
            
            return SendLinkedInOutreachResponse(
                success=outreach_sent,
                candidate=request.candidate,
                outreach_sent=outreach_sent,
                outreach_type=request.outreach_type,
                delivery_status=delivery_status,
                message_id=message_id,
                error=error,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error executing LinkedIn outreach: {e}")
            return SendLinkedInOutreachResponse(
                success=False,
                candidate=request.candidate,
                outreach_sent=False,
                outreach_type=request.outreach_type,
                delivery_status="error",
                error=str(e)
            )
    
    def _extract_linkedin_id(self, linkedin_url: str) -> Optional[str]:
        """Extract LinkedIn ID from URL."""
        try:
            # Handle various LinkedIn URL formats
            if "/in/" in linkedin_url:
                parts = linkedin_url.split("/in/")
                if len(parts) > 1:
                    id_part = parts[1].split("/")[0].split("?")[0]
                    return id_part
            elif "/profile/view?id=" in linkedin_url:
                parts = linkedin_url.split("id=")
                if len(parts) > 1:
                    return parts[1].split("&")[0]
            else:
                # Assume it's already an ID
                return linkedin_url.split("/")[-1].split("?")[0]
            
            return None
        except Exception as e:
            logger.warning(f"Error extracting LinkedIn ID: {e}")
            return None
    
    def _generate_default_message(
        self,
        candidate: Candidate,
        project: Project,
        personalization_data: Dict[str, Any]
    ) -> str:
        """Generate default LinkedIn message."""
        skills_mention = ", ".join(list(candidate.skills.skills)[:3]) if candidate.skills.skills else "your background"
        
        message = f"""Hi {candidate.name},

I hope this message finds you well. I'm reaching out about a {project.title} opportunity at {project.company}.

Based on your background in {skills_mention}, I thought you might be interested in this role.

Would you be open to a brief conversation to discuss this opportunity?

Best regards,
Recruitment Team"""
        
        return message

