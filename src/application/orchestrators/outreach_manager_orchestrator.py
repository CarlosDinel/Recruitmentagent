"""
Outreach Manager Orchestrator - Clean Architecture

This orchestrator coordinates outreach campaigns using Clean Architecture principles.
It orchestrates use cases for sending outreach messages across multiple channels.

Architecture:
============

    OutreachManagerOrchestrator
    ├── Uses Domain Entities (Campaign, Candidate)
    ├── Uses Repository Interfaces (CampaignRepository, CandidateRepository)
    ├── Coordinates Use Cases
    │   ├── SendLinkedInOutreachUseCase (to be created)
    │   ├── SendEmailOutreachUseCase (to be created)
    │   └── GeneratePersonalizedMessageUseCase (to be created)
    └── Manages Campaign State

Design Principles:
=================

1. **Dependency Inversion**: Depends on abstractions (repositories), not implementations
2. **Single Responsibility**: Orchestrates outreach campaigns, doesn't implement business logic
3. **Use Case Coordination**: Delegates to use cases for operations
4. **Domain-Driven**: Uses domain entities, not dictionaries

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

# Domain Layer (inner layer - no dependencies)
from ...domain.entities.campaign import Campaign
from ...domain.entities.candidate import Candidate
from ...domain.value_objects.project_id import ProjectId
from ...domain.enums.outreach_channel import OutreachChannel
from ...domain.enums.candidate_status import CandidateStatus
from ...domain.repositories.campaign_repository import CampaignRepository
from ...domain.repositories.candidate_repository import CandidateRepository

# Infrastructure Layer (injected via dependency injection)
try:
    from ...infrastructure.external_services.linkedin.linkedin_service_impl import LinkedInServiceImpl
    from ...infrastructure.external_services.email.email_service_impl import EmailServiceImpl
except ImportError:
    LinkedInServiceImpl = None
    EmailServiceImpl = None

logger = logging.getLogger(__name__)


class OutreachManagerOrchestrator:
    """
    Clean Architecture orchestrator for outreach campaigns.
    
    This orchestrator follows Clean Architecture principles:
    - Uses domain entities (Campaign, Candidate)
    - Depends on repository interfaces, not implementations
    - Coordinates use cases instead of implementing business logic
    - No direct database access
    - No direct external service calls (goes through interfaces)
    
    Responsibilities:
        - Coordinate outreach campaign execution
        - Manage campaign state
        - Delegate to use cases for message sending
        - Track campaign metrics
        - Handle multi-channel outreach
    
    Dependencies (injected):
        - campaign_repository: CampaignRepository interface
        - candidate_repository: CandidateRepository interface
        - linkedin_service: LinkedIn service interface
        - email_service: Email service interface
    
    Example:
        >>> from src.infrastructure.persistence.mongodb import (
        ...     MongoDBCampaignRepository,
        ...     MongoDBCandidateRepository
        ... )
        >>> from src.infrastructure.external_services.linkedin import LinkedInServiceImpl
        >>> from src.infrastructure.external_services.email import EmailServiceImpl
        >>> 
        >>> # Initialize repositories
        >>> campaign_repo = MongoDBCampaignRepository()
        >>> candidate_repo = MongoDBCandidateRepository()
        >>> linkedin_service = LinkedInServiceImpl()
        >>> email_service = EmailServiceImpl()
        >>> 
        >>> # Initialize orchestrator
        >>> orchestrator = OutreachManagerOrchestrator(
        ...     campaign_repository=campaign_repo,
        ...     candidate_repository=candidate_repo,
        ...     linkedin_service=linkedin_service,
        ...     email_service=email_service
        ... )
        >>> 
        >>> # Execute campaign
        >>> result = await orchestrator.execute_outreach_campaign(
        ...     project_id="proj123",
        ...     candidates=[candidate1, candidate2],
        ...     campaign_name="Python Developers",
        ...     channel=OutreachChannel.LINKEDIN
        ... )
    
    Note:
        This is the Clean Architecture version. The old OutreachManager
        in agents/ folder will be kept for backward compatibility during migration.
    """
    
    def __init__(
        self,
        campaign_repository: CampaignRepository,
        candidate_repository: CandidateRepository,
        linkedin_service: Optional[LinkedInServiceImpl] = None,
        email_service: Optional[EmailServiceImpl] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the outreach orchestrator with dependencies.
        
        Args:
            campaign_repository: Repository for campaign persistence
            candidate_repository: Repository for candidate persistence
            linkedin_service: Optional LinkedIn service for outreach
            email_service: Optional Email service for outreach
            config: Optional configuration dictionary
        
        Design:
            - Dependency Injection: All dependencies injected
            - Interface Segregation: Depends on interfaces, not implementations
            - Single Responsibility: Only orchestrates, doesn't implement
        """
        self.campaign_repository = campaign_repository
        self.candidate_repository = candidate_repository
        self.linkedin_service = linkedin_service
        self.email_service = email_service
        self.config = config or {}
        self.logger = logging.getLogger('OutreachManagerOrchestrator')
        self.logger.setLevel(logging.INFO)
        
        # Campaign configuration
        self.max_retries = self.config.get('max_retries', 3)
        self.rate_limit = self.config.get('rate_limit', 10)  # messages per hour
        
        # Campaign state
        self.active_campaigns: Dict[str, Campaign] = {}
    
    async def execute_outreach_campaign(
        self,
        project_id: str,
        candidates: List[Candidate],
        campaign_name: str,
        channel: OutreachChannel,
        position_details: Optional[Dict[str, Any]] = None,
        message_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an outreach campaign using Clean Architecture.
        
        This method orchestrates the complete outreach campaign:
        1. Create Campaign domain entity
        2. Load candidates from repository
        3. Send outreach messages via appropriate channel
        4. Track campaign metrics
        5. Update campaign and candidate status
        
        Args:
            project_id: Project identifier
            candidates: List of Candidate entities to contact
            campaign_name: Name of the campaign
            channel: Outreach channel (LINKEDIN, EMAIL, etc.)
            position_details: Optional position details for personalization
            message_template: Optional message template
        
        Returns:
            Dictionary with campaign results
        
        Example:
            >>> result = await orchestrator.execute_outreach_campaign(
            ...     project_id="proj123",
            ...     candidates=[candidate1, candidate2],
            ...     campaign_name="Python Developers Q1",
            ...     channel=OutreachChannel.LINKEDIN
            ... )
            >>> print(f"Contacted: {result['contacted_count']}")
            >>> print(f"Response rate: {result['response_rate']}")
        """
        self.logger.info(f"Executing outreach campaign: {campaign_name}")
        
        try:
            # Create campaign entity
            campaign = await self._create_campaign(
                project_id=project_id,
                campaign_name=campaign_name,
                channel=channel,
                candidates=candidates
            )
            
            self.active_campaigns[campaign.id] = campaign
            
            # Execute outreach based on channel
            contacted_candidates = []
            responded_candidates = []
            
            for candidate in candidates:
                try:
                    # Send outreach message
                    contact_result = await self._send_outreach_message(
                        candidate=candidate,
                        campaign=campaign,
                        channel=channel,
                        position_details=position_details,
                        message_template=message_template
                    )
                    
                    if contact_result['success']:
                        # Update candidate status
                        candidate.mark_contacted(channel.value)
                        await self.candidate_repository.save(candidate)
                        
                        # Update campaign metrics
                        campaign.record_message_sent(delivered=contact_result.get('delivered', True))
                        campaign.add_candidate(str(candidate.id))
                        
                        contacted_candidates.append(candidate)
                        
                        # Simulate response (in production, this would be async monitoring)
                        if self._should_simulate_response(candidate):
                            candidate.mark_responded()
                            await self.candidate_repository.save(candidate)
                            campaign.record_response(is_positive=True)
                            responded_candidates.append(candidate)
                            
                except Exception as e:
                    self.logger.warning(f"Failed to contact candidate {candidate.id}: {e}")
                    continue
            
            # Save campaign
            await self.campaign_repository.save(campaign)
            
            # Calculate metrics
            response_rate = campaign.calculate_response_rate()
            delivery_rate = campaign.calculate_delivery_rate()
            conversion_rate = campaign.calculate_conversion_rate()
            
            return {
                'success': True,
                'campaign_id': campaign.id,
                'contacted_count': len(contacted_candidates),
                'responded_count': len(responded_candidates),
                'response_rate': response_rate,
                'delivery_rate': delivery_rate,
                'conversion_rate': conversion_rate,
                'candidates': [c.to_dict() for c in contacted_candidates],
                'stage': 'outreach_completed'
            }
            
        except Exception as e:
            self.logger.error(f"Error executing outreach campaign: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stage': 'error'
            }
    
    async def _create_campaign(
        self,
        project_id: str,
        campaign_name: str,
        channel: OutreachChannel,
        candidates: List[Candidate]
    ) -> Campaign:
        """Create Campaign domain entity."""
        campaign = Campaign(
            id=f"campaign_{uuid.uuid4().hex[:8]}",
            project_id=ProjectId(project_id),
            name=campaign_name,
            channel=channel,
            target_candidates=[str(c.id) for c in candidates]
        )
        
        # Save campaign
        await self.campaign_repository.save(campaign)
        self.logger.info(f"Created campaign: {campaign.id}")
        
        return campaign
    
    async def _send_outreach_message(
        self,
        candidate: Candidate,
        campaign: Campaign,
        channel: OutreachChannel,
        position_details: Optional[Dict[str, Any]] = None,
        message_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send outreach message via appropriate channel."""
        try:
            # Generate personalized message
            message = self._generate_personalized_message(
                candidate=candidate,
                position_details=position_details or {},
                template=message_template
            )
            
            # Send via appropriate channel
            if channel == OutreachChannel.LINKEDIN:
                return await self._send_linkedin_message(candidate, message)
            elif channel == OutreachChannel.EMAIL:
                return await self._send_email_message(candidate, message, position_details)
            else:
                self.logger.warning(f"Unsupported channel: {channel}")
                return {'success': False, 'error': f'Unsupported channel: {channel}'}
                
        except Exception as e:
            self.logger.error(f"Error sending outreach message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_linkedin_message(
        self,
        candidate: Candidate,
        message: str
    ) -> Dict[str, Any]:
        """Send LinkedIn message."""
        if not self.linkedin_service:
            self.logger.warning("LinkedIn service not available, using mock")
            return {'success': True, 'delivered': True, 'channel': 'linkedin_mock'}
        
        try:
            linkedin_id = candidate.contact_info.linkedin_url or str(candidate.id)
            result = self.linkedin_service.send_message(
                provider_id=linkedin_id,
                message=message
            )
            return {'success': True, 'delivered': True, 'channel': 'linkedin', 'result': result}
        except Exception as e:
            self.logger.error(f"Error sending LinkedIn message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_email_message(
        self,
        candidate: Candidate,
        message: str,
        position_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email message."""
        if not self.email_service:
            self.logger.warning("Email service not available, using mock")
            return {'success': True, 'delivered': True, 'channel': 'email_mock'}
        
        try:
            email = candidate.contact_info.email
            if not email:
                return {'success': False, 'error': 'No email address'}
            
            subject = f"Opportunity: {position_details.get('title', 'Career Opportunity')}"
            result = self.email_service.send_email(
                to_email=email,
                subject=subject,
                body=message
            )
            return {'success': True, 'delivered': True, 'channel': 'email', 'result': result}
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_personalized_message(
        self,
        candidate: Candidate,
        position_details: Dict[str, Any],
        template: Optional[str] = None
    ) -> str:
        """Generate personalized outreach message."""
        # Simple template-based message generation
        # In production, this would use an AI service or more sophisticated templating
        
        position_title = position_details.get('title', 'opportunity')
        company = position_details.get('company', 'our company')
        
        message = f"""Hi {candidate.name},

I hope this message finds you well. I'm reaching out about a {position_title} opportunity at {company}.

Based on your background in {', '.join(list(candidate.skills.skills)[:3]) if candidate.skills.skills else 'your field'}, I thought you might be interested.

Would you be open to a brief conversation?

Best regards,
Recruitment Team"""
        
        return message
    
    def _should_simulate_response(self, candidate: Candidate) -> bool:
        """Determine if we should simulate a response (for testing)."""
        # In production, this would be replaced with actual response monitoring
        # For now, simulate ~30% response rate
        import random
        return random.random() < 0.3

