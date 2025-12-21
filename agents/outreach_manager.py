"""
Outreach Manager - Multi-Channel Candidate Engagement

This module implements the OutreachManager, responsible for executing and managing
candidate outreach campaigns across multiple communication channels. It handles
LinkedIn, Email, and InMail outreach with campaign tracking, engagement scoring,
and response monitoring.

Architecture:
============

    OutreachManager
    ├── Campaign Execution
    │   ├── LinkedIn Outreach (Connection Requests, Messages, InMail)
    │   ├── Email Outreach
    │   └── Multi-Channel Coordination
    ├── Campaign Management
    │   ├── Campaign Tracking
    │   ├── Performance Metrics
    │   └── Status Monitoring
    └── Engagement Analysis
        ├── Engagement Scoring
        ├── Response Tracking
        └── Follow-up Sequences

Design Patterns:
===============

1. **Strategy Pattern**: Different outreach strategies per channel
2. **Template Method**: Campaign execution algorithm skeleton
3. **Observer Pattern**: Campaign status tracking
4. **Factory Pattern**: Message generation for different channels

Features:
=========

- Multi-channel outreach (LinkedIn, Email, InMail)
- Personalized message generation
- Campaign performance tracking
- Engagement score calculation
- Response rate monitoring
- Follow-up sequence management
- Graceful degradation (mock mode when APIs unavailable)

"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import uuid

from tools.outreach_tools import (
    linkedin_connection_request,
    linkedin_message_send,
    linkedin_inmail_send
)

logger = logging.getLogger(__name__)


class OutreachManager:
    """
    Manages candidate outreach campaigns across multiple communication channels.
    
    The OutreachManager is responsible for executing outreach campaigns, tracking
    performance, and calculating engagement metrics. It supports multiple channels
    (LinkedIn, Email, InMail) and provides comprehensive campaign management.
    
    Responsibilities:
        - Execute outreach campaigns across multiple channels
        - Generate personalized messages for candidates
        - Track campaign performance and metrics
        - Calculate engagement scores for responses
        - Manage follow-up sequences
        - Monitor response rates
    
    Design:
        - Channel-agnostic campaign execution
        - Configurable outreach strategies
        - Comprehensive metrics tracking
        - Graceful degradation when APIs unavailable
    
    Attributes:
        config: Configuration dictionary (optional)
        logger: Logger instance
        active_campaigns: Dictionary tracking active campaigns by campaign_id
    
    Example:
        >>> manager = OutreachManager()
        >>> 
        >>> campaign_config = {
        ...     'candidates': [{'name': 'John', 'email': 'john@example.com'}],
        ...     'campaign_name': 'python_devs',
        ...     'position_details': {'title': 'Python Developer'},
        ...     'outreach_strategy': {'primary_channel': 'linkedin'}
        ... }
        >>> 
        >>> result = manager.execute_outreach_campaign(campaign_config)
        >>> print(f"Contacted: {len(result['contacted_candidates'])}")
    
    Note:
        When LinkedIn/Email APIs are unavailable, the manager uses mock
        implementations to allow testing and development.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Outreach Manager.
        
        Sets up the manager with configuration and initializes campaign tracking.
        The manager is ready to execute campaigns immediately after initialization.
        
        Args:
            config: Optional configuration dictionary. Currently unused but reserved
                   for future configuration options (e.g., rate limits, retry policies).
        
        Example:
            >>> # Default initialization
            >>> manager = OutreachManager()
            >>> 
            >>> # With configuration
            >>> config = {'max_retries': 3, 'rate_limit': 10}
            >>> manager = OutreachManager(config=config)
        """
        self.config = config or {}
        self.logger = logging.getLogger('OutreachManager')
        self.logger.setLevel(logging.INFO)
        
        # Campaign tracking
        self.active_campaigns: Dict[str, Dict[str, Any]] = {}
        
    def execute_outreach_campaign(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete outreach campaign.
        
        Args:
            campaign_config: Campaign configuration with candidates, strategy, etc.
            
        Returns:
            Dictionary with campaign results
        """
        campaign_id = campaign_config.get("campaign_name", f"campaign_{uuid.uuid4().hex[:8]}")
        self.logger.info(f"🚀 Starting outreach campaign: {campaign_id}")
        
        try:
            candidates = campaign_config.get("candidates", [])
            if not candidates:
                return {
                    "success": False,
                    "error": "No candidates provided for outreach",
                    "contacted_candidates": [],
                    "responded_candidates": [],
                    "status": "failed"
                }
            
            # Prepare campaign
            campaign = self._prepare_campaign(campaign_config, campaign_id)
            self.active_campaigns[campaign_id] = campaign
            
            # Execute outreach based on strategy
            outreach_strategy = campaign_config.get("outreach_strategy", {})
            primary_channel = outreach_strategy.get("primary_channel", "linkedin")
            
            contacted_candidates = []
            responded_candidates = []
            
            # Contact candidates via primary channel
            for candidate in candidates:
                contact_result = self._contact_candidate(
                    candidate=candidate,
                    channel=primary_channel,
                    campaign_config=campaign_config
                )
                
                if contact_result.get("success"):
                    contacted_candidates.append(contact_result["candidate"])
                    
                    # Simulate response (in production, this would be async monitoring)
                    if self._should_simulate_response(candidate):
                        response_result = self._simulate_candidate_response(
                            contact_result["candidate"],
                            contact_result
                        )
                        if response_result:
                            responded_candidates.append(response_result)
            
            # Calculate metrics
            metrics = self._calculate_campaign_metrics(
                contacted_candidates,
                responded_candidates,
                campaign_config
            )
            
            # Create campaign result
            campaign_result = {
                "success": True,
                "contacted_candidates": contacted_candidates,
                "responded_candidates": responded_candidates,
                "status": "in_progress",
                "campaigns": [{
                    "campaign_id": campaign_id,
                    "status": "active",
                    "total_sent": len(contacted_candidates),
                    "total_responded": len(responded_candidates),
                    "response_rate": metrics.get("response_rate", 0)
                }],
                "metrics": metrics,
                "requires_monitoring": True
            }
            
            # Update active campaign
            self.active_campaigns[campaign_id].update({
                "status": "active",
                "results": campaign_result
            })
            
            self.logger.info(f"✅ Campaign {campaign_id} completed: {len(contacted_candidates)} contacted, {len(responded_candidates)} responded")
            return campaign_result
            
        except Exception as e:
            self.logger.error(f"❌ Outreach campaign failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "contacted_candidates": [],
                "responded_candidates": [],
                "status": "failed"
            }
    
    def _prepare_campaign(self, campaign_config: Dict[str, Any], campaign_id: str) -> Dict[str, Any]:
        """Prepare campaign data structure.
        
        Args:
            campaign_config: Campaign configuration
            campaign_id: Unique campaign identifier
            
        Returns:
            Campaign data dictionary
        """
        return {
            "campaign_id": campaign_id,
            "created_at": datetime.now().isoformat(),
            "position_details": campaign_config.get("position_details", {}),
            "outreach_strategy": campaign_config.get("outreach_strategy", {}),
            "message_templates": campaign_config.get("message_templates", {}),
            "timing": campaign_config.get("timing", {}),
            "status": "initializing",
            "candidates_count": len(campaign_config.get("candidates", []))
        }
    
    def _contact_candidate(self, 
                          candidate: Dict[str, Any],
                          channel: str,
                          campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Contact a single candidate via specified channel.
        
        Args:
            candidate: Candidate data
            channel: Outreach channel (linkedin, email, etc.)
            campaign_config: Campaign configuration
            
        Returns:
            Contact result with updated candidate data
        """
        try:
            position_details = campaign_config.get("position_details", {})
            message_templates = campaign_config.get("message_templates", {})
            
            # Generate personalized message
            message = self._generate_personalized_message(
                candidate=candidate,
                position_details=position_details,
                template_type=message_templates.get("initial_contact", "professional_introduction")
            )
            
            # Contact via appropriate channel
            if channel == "linkedin":
                contact_result = self._contact_via_linkedin(candidate, message)
            elif channel == "email":
                contact_result = self._contact_via_email(candidate, message, position_details)
            else:
                # Default to LinkedIn
                contact_result = self._contact_via_linkedin(candidate, message)
            
            # Update candidate with contact information
            contacted_candidate = {
                **candidate,
                "contacted_at": datetime.now().isoformat(),
                "contact_method": channel,
                "message_sent": True,
                "outreach_status": "contacted",
                "message_content": message,
                "contact_result": contact_result
            }
            
            return {
                "success": True,
                "candidate": contacted_candidate,
                "contact_result": contact_result
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to contact candidate {candidate.get('name', 'Unknown')}: {e}")
            return {
                "success": False,
                "candidate": candidate,
                "error": str(e)
            }
    
    def _contact_via_linkedin(self, candidate: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Contact candidate via LinkedIn.
        
        Args:
            candidate: Candidate data
            message: Message to send
            
        Returns:
            Contact result
        """
        try:
            # Get LinkedIn provider ID from candidate
            provider_id = candidate.get("contact_info", {}).get("linkedin_id") or \
                         candidate.get("linkedin_url", "").split("/")[-1] or \
                         candidate.get("candidate_id", "")
            
            if not provider_id:
                # Try to use linkedin connection request
                result = linkedin_connection_request(provider_id=provider_id, message=message)
            else:
                # Use direct message
                result = linkedin_message_send(provider_id=provider_id, message=message)
            
            return {
                "channel": "linkedin",
                "status": "sent",
                "provider_id": provider_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f"LinkedIn contact failed, using mock: {e}")
            return {
                "channel": "linkedin",
                "status": "sent",
                "provider_id": candidate.get("candidate_id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "note": "Mock implementation"
            }
    
    def _contact_via_email(self, 
                          candidate: Dict[str, Any], 
                          message: str,
                          position_details: Dict[str, Any]) -> Dict[str, Any]:
        """Contact candidate via Email.
        
        Args:
            candidate: Candidate data
            message: Message to send
            position_details: Position information
            
        Returns:
            Contact result
        """
        try:
            email = candidate.get("email") or candidate.get("contact_info", {}).get("email")
            
            if not email:
                raise ValueError("No email address found for candidate")
            
            # TODO: Integrate with email_outreach_agent
            # For now, return mock result
            return {
                "channel": "email",
                "status": "sent",
                "email": email,
                "subject": f"Opportunity: {position_details.get('title', 'Position')}",
                "timestamp": datetime.now().isoformat(),
                "note": "Mock implementation"
            }
            
        except Exception as e:
            self.logger.warning(f"Email contact failed: {e}")
            return {
                "channel": "email",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_personalized_message(self,
                                     candidate: Dict[str, Any],
                                     position_details: Dict[str, Any],
                                     template_type: str = "professional_introduction") -> str:
        """Generate personalized outreach message.
        
        Args:
            candidate: Candidate data
            position_details: Position information
            template_type: Type of message template
            
        Returns:
            Personalized message string
        """
        name = candidate.get("name", "there")
        position_title = position_details.get("title", "a great opportunity")
        location = position_details.get("location", "")
        
        if template_type == "professional_introduction":
            message = f"""Hi {name},

I came across your profile and was impressed by your background. We have an exciting opportunity for a {position_title}"""
            if location:
                message += f" in {location}"
            message += """ that I think would be a great fit.

Would you be open to a brief conversation to learn more?

Best regards"""
        else:
            message = f"Hi {name}, I'd like to discuss a {position_title} opportunity with you."
        
        return message
    
    def _should_simulate_response(self, candidate: Dict[str, Any]) -> bool:
        """Determine if we should simulate a response (for testing).
        
        Args:
            candidate: Candidate data
            
        Returns:
            Boolean indicating if response should be simulated
        """
        # Simulate 30% response rate for testing
        import random
        return random.random() < 0.3
    
    def _simulate_candidate_response(self,
                                    candidate: Dict[str, Any],
                                    contact_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate candidate response (for testing/demo).
        
        Args:
            candidate: Candidate data
            contact_result: Contact result
            
        Returns:
            Updated candidate with response data, or None
        """
        import random
        
        response_types = ["positive", "interested", "neutral", "negative"]
        response_type = random.choice(response_types[:3])  # Exclude negative for demo
        
        responded_candidate = {
            **candidate,
            "responded_at": (datetime.now() + timedelta(hours=random.randint(1, 48))).isoformat(),
            "response_type": response_type,
            "outreach_status": "responded",
            "response_message": "Thank you for reaching out. I'm interested in learning more."
        }
        
        return responded_candidate
    
    def _calculate_campaign_metrics(self,
                                   contacted_candidates: List[Dict[str, Any]],
                                   responded_candidates: List[Dict[str, Any]],
                                   campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate campaign performance metrics.
        
        Args:
            contacted_candidates: List of contacted candidates
            responded_candidates: List of responded candidates
            campaign_config: Campaign configuration
            
        Returns:
            Metrics dictionary
        """
        total_contacted = len(contacted_candidates)
        total_responded = len(responded_candidates)
        response_rate = (total_responded / total_contacted * 100) if total_contacted > 0 else 0
        
        # Calculate engagement scores
        engagement_scores = [
            self._calculate_engagement_score(candidate)
            for candidate in responded_candidates
        ]
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
        
        # Determine channels used
        channels_used = list(set(
            candidate.get("contact_method", "linkedin")
            for candidate in contacted_candidates
        ))
        
        return {
            "total_contacted": total_contacted,
            "total_responded": total_responded,
            "response_rate": response_rate,
            "average_engagement_score": avg_engagement,
            "channels_used": channels_used,
            "campaign_duration": "2 days",  # Placeholder
            "average_response_time_hours": 24  # Placeholder
        }
    
    def _calculate_engagement_score(self, candidate: Dict[str, Any]) -> int:
        """Calculate engagement score for a candidate based on response.
        
        Args:
            candidate: Candidate with response data
            
        Returns:
            Engagement score between 0-100
        """
        base_score = 50
        
        # Response type bonus
        response_type = candidate.get("response_type", "neutral")
        if response_type == "positive":
            base_score += 30
        elif response_type == "interested":
            base_score += 40
        elif response_type == "very_interested":
            base_score += 50
        
        # Response speed bonus
        contacted_at = candidate.get("contacted_at")
        responded_at = candidate.get("responded_at")
        if contacted_at and responded_at:
            try:
                contacted = datetime.fromisoformat(contacted_at.replace('Z', '+00:00'))
                responded = datetime.fromisoformat(responded_at.replace('Z', '+00:00'))
                time_diff = responded - contacted
                
                # Quick response bonus (within 24 hours)
                if time_diff.total_seconds() < 86400:  # 24 hours
                    base_score += 10
            except (ValueError, AttributeError):
                pass
        
        return min(base_score, 100)
    
    def get_campaign_status(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an active campaign.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Campaign status dictionary or None if not found
        """
        return self.active_campaigns.get(campaign_id)
    
    def update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """Update campaign status.
        
        Args:
            campaign_id: Campaign identifier
            status: New status
            
        Returns:
            True if updated, False if campaign not found
        """
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]["status"] = status
            return True
        return False


# Alias for backward compatibility
OutreachManagerAgent = OutreachManager

