"""
Generate Personalized Message Use Case - Clean Architecture

This use case generates personalized outreach messages for candidates.
It follows Clean Architecture principles by using domain entities and services.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ....domain.entities.candidate import Candidate
from ....domain.entities.project import Project

# Infrastructure services (injected)
try:
    from ....infrastructure.ai.openai_service import OpenAIService
except ImportError:
    OpenAIService = None

logger = logging.getLogger(__name__)


class GeneratePersonalizedMessageRequest:
    """Request DTO for generating personalized messages."""
    
    def __init__(
        self,
        candidate: Candidate,
        project: Project,
        message_type: str = "first_contact",  # "first_contact", "follow_up", "meeting_invitation"
        user_info: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None,
        sector: Optional[str] = None,
        tone: str = "professional"  # "professional", "casual", "friendly"
    ):
        self.candidate = candidate
        self.project = project
        self.message_type = message_type
        self.user_info = user_info or {}
        self.conversation_history = conversation_history or []
        self.sector = sector
        self.tone = tone


class GeneratePersonalizedMessageResponse:
    """Response DTO for personalized message generation."""
    
    def __init__(
        self,
        message: str,
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.subject = subject
        self.metadata = metadata or {}


class GeneratePersonalizedMessageUseCase:
    """
    Use case for generating personalized outreach messages.
    
    This use case generates personalized messages for candidates using AI services.
    It follows Clean Architecture by using infrastructure services through interfaces.
    
    Example:
        >>> use_case = GeneratePersonalizedMessageUseCase(
        ...     ai_service=openai_service
        ... )
        >>> 
        >>> request = GeneratePersonalizedMessageRequest(
        ...     candidate=candidate,
        ...     project=project,
        ...     message_type="first_contact",
        ...     tone="professional"
        ... )
        >>> 
        >>> response = await use_case.execute(request)
        >>> print(response.message)
    """
    
    def __init__(
        self,
        ai_service: Optional[Any] = None  # AI service interface
    ):
        """
        Initialize generate personalized message use case.
        
        Args:
            ai_service: Optional AI service for message generation
        """
        self.ai_service = ai_service
        logger.info("GeneratePersonalizedMessageUseCase initialized")
    
    async def execute(self, request: GeneratePersonalizedMessageRequest) -> GeneratePersonalizedMessageResponse:
        """
        Execute message generation.
        
        Args:
            request: Message generation request with candidate and project
        
        Returns:
            Message generation response with personalized message
        """
        logger.info(f"Generating {request.message_type} message for {request.candidate.name}")
        
        try:
            # Generate message using AI service or template
            if self.ai_service:
                message = await self._generate_with_ai(request)
            else:
                message = self._generate_with_template(request)
            
            # Generate subject if needed
            subject = self._generate_subject(request)
            
            metadata = {
                "generated_at": datetime.now().isoformat(),
                "message_type": request.message_type,
                "tone": request.tone,
                "sector": request.sector,
                "word_count": len(message.split())
            }
            
            return GeneratePersonalizedMessageResponse(
                message=message,
                subject=subject,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error generating personalized message: {e}")
            # Fallback to template-based message
            message = self._generate_with_template(request)
            subject = self._generate_subject(request)
            
            return GeneratePersonalizedMessageResponse(
                message=message,
                subject=subject,
                metadata={"error": str(e), "fallback": True}
            )
    
    async def _generate_with_ai(self, request: GeneratePersonalizedMessageRequest) -> str:
        """Generate message using AI service."""
        # This would use the AI service to generate personalized messages
        # For now, fallback to template
        return self._generate_with_template(request)
    
    def _generate_with_template(self, request: GeneratePersonalizedMessageRequest) -> str:
        """Generate message using template."""
        candidate = request.candidate
        project = request.project
        
        # Extract key information
        candidate_name = candidate.name.split()[0] if candidate.name else "there"
        skills_mention = ", ".join(list(candidate.skills.skills)[:3]) if candidate.skills.skills else "your background"
        position = candidate.current_position or "your current role"
        company = candidate.current_company or "your current company"
        
        # Generate based on message type
        if request.message_type == "first_contact":
            message = f"""Hi {candidate_name},

I hope this message finds you well. I'm reaching out about a {project.title} opportunity at {project.company}.

Based on your experience as {position} at {company} and your background in {skills_mention}, I thought you might be interested in this role.

{project.description[:200]}{"..." if len(project.description) > 200 else ""}

Would you be open to a brief conversation to discuss this opportunity?

Best regards,
{request.user_info.get('name', 'Recruitment Team')}"""
        
        elif request.message_type == "follow_up":
            message = f"""Hi {candidate_name},

I wanted to follow up on my previous message about the {project.title} opportunity at {project.company}.

I believe your experience in {skills_mention} would be a great fit for this role.

Would you be available for a quick call this week?

Best regards,
{request.user_info.get('name', 'Recruitment Team')}"""
        
        elif request.message_type == "meeting_invitation":
            message = f"""Hi {candidate_name},

Thank you for your interest in the {project.title} role at {project.company}.

I'd like to invite you to a brief conversation to discuss this opportunity in more detail.

Would you be available for a call this week? Please let me know your preferred time.

Best regards,
{request.user_info.get('name', 'Recruitment Team')}"""
        
        else:
            # Default message
            message = f"""Hi {candidate_name},

I'm reaching out about a {project.title} opportunity at {project.company}.

Based on your background, I thought you might be interested.

Would you be open to a conversation?

Best regards,
{request.user_info.get('name', 'Recruitment Team')}"""
        
        return message
    
    def _generate_subject(self, request: GeneratePersonalizedMessageRequest) -> str:
        """Generate email subject line."""
        if request.message_type == "first_contact":
            return f"Opportunity: {request.project.title} at {request.project.company}"
        elif request.message_type == "follow_up":
            return f"Following up: {request.project.title} at {request.project.company}"
        elif request.message_type == "meeting_invitation":
            return f"Meeting invitation: {request.project.title} at {request.project.company}"
        else:
            return f"Career opportunity at {request.project.company}"

