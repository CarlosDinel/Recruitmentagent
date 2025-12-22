"""
LinkedIn Outreach Agent - Manages LinkedIn recruitment outreach activities.
Sends messages, InMails, connection requests, and engages with posts.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools.outreach_tools import (
    linkedin_connection_request,
    linkedin_message_send,
    linkedin_inmail_send,
    linkedin_post_reaction_like,
    send_outreach_email
)
from agents.database_agent import DatabaseAgent
from prompts.LinkedIn_outreach_agent_prompts import LinkedInOutreachPrompts

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInOutreachAgent:
    """
    Agent that manages LinkedIn recruitment outreach including:
    - Sending connection requests
    - Sending direct messages
    - Sending InMails (premium messages)
    - Liking candidate posts for engagement
    
    All actions are logged in the Database Agent for tracking.
    """
    
    def __init__(self, user_info: Dict[str, Any], llm_provider: str = "openai"):
        """
        Initialize the LinkedIn Outreach Agent.
        
        Args:
            user_info: User/recruiter context (voornaam, bedrijfsnaam, etc.)
            llm_provider: AI provider to use ("openai" or "anthropic")
        """
        self.user_info = user_info
        self.db_agent = DatabaseAgent()
        self.llm_provider = llm_provider
        
        # Initialize LLM for message generation
        if llm_provider == "openai":
            self.llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                temperature=0.7,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        
        logger.info(f"✅ LinkedInOutreachAgent initialized for {user_info.get('voornaam', 'user')}")
    
    def send_connection_request(
        self,
        provider_id: str,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        campaign_num: str,
        personalized_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a LinkedIn connection request with optional personalized message.
        
        Args:
            provider_id: LinkedIn user ID (unique identifier)
            candidate_name: Candidate's first name
            candidate_info: Candidate details for context
            project_info: Project/job information
            campaign_num: Campaign number for tracking
            personalized_message: Optional custom message
        
        Returns:
            Report for Outreach Manager
        """
        try:
            logger.info(f"📤 Sending connection request to {provider_id}")
            
            # Generate personalized message if not provided
            if not personalized_message:
                personalized_message = self._generate_connection_message(
                    candidate_name, candidate_info, project_info
                )
            
            # Execute LinkedIn tool
            tool_result = linkedin_connection_request(provider_id, personalized_message)
            
            if tool_result["status"] != "success":
                raise Exception(tool_result.get("error", "Unknown error"))
            
            # Update Database Agent
            db_result = self.db_agent.tools.update_candidate_status(
                linkedin_url=candidate_info.get("linkedin_url", ""),
                updates={
                    "connectie_verzoek": True,
                    "connectie_verzoek_datum": datetime.utcnow().isoformat(),
                    "projectid": project_info["projectid"],
                    "project_naam": project_info["project_name"],
                    "campaign_num": campaign_num,
                    "last_contact": "connection_request",
                    "last_contact_date": datetime.utcnow().isoformat()
                }
            )
            
            # Prepare report
            report = {
                "action": "connection_request",
                "candidate_name": candidate_name,
                "provider_id": provider_id,
                "linkedin_tool_confirmation": tool_result,
                "database_update_confirmation": db_result,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ Connection request sent and logged: {provider_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error sending connection request: {e}")
            return {
                "action": "connection_request",
                "status": "error",
                "error": str(e),
                "provider_id": provider_id
            }
    
    def send_linkedin_message(
        self,
        provider_id: str,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        campaign_num: str,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a LinkedIn direct message to a candidate.
        
        Args:
            provider_id: LinkedIn user ID
            candidate_name: Candidate's first name
            candidate_info: Candidate details
            project_info: Project/job information
            campaign_num: Campaign number
            custom_message: Optional custom message
        
        Returns:
            Report for Outreach Manager
        """
        try:
            logger.info(f"💬 Sending LinkedIn message to {provider_id}")
            
            # Generate message if not provided
            if not custom_message:
                custom_message = self._generate_linkedin_message(
                    candidate_name, candidate_info, project_info
                )
            
            # Execute LinkedIn tool
            tool_result = linkedin_message_send(provider_id, custom_message)
            
            if tool_result["status"] != "success":
                raise Exception(tool_result.get("error", "Unknown error"))
            
            # Update Database Agent
            db_result = self.db_agent.tools.update_candidate_status(
                linkedin_url=candidate_info.get("linkedin_url", ""),
                updates={
                    "linkedin_bericht": True,
                    "linkedin_bericht_datum": datetime.utcnow().isoformat(),
                    "projectid": project_info["projectid"],
                    "project_naam": project_info["project_name"],
                    "campaign_num": campaign_num,
                    "last_contact": "linkedin_message",
                    "last_contact_date": datetime.utcnow().isoformat()
                }
            )
            
            # Prepare report
            report = {
                "action": "linkedin_message",
                "candidate_name": candidate_name,
                "provider_id": provider_id,
                "message_preview": custom_message[:100] + "..." if len(custom_message) > 100 else custom_message,
                "linkedin_tool_confirmation": tool_result,
                "database_update_confirmation": db_result,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ LinkedIn message sent and logged: {provider_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error sending LinkedIn message: {e}")
            return {
                "action": "linkedin_message",
                "status": "error",
                "error": str(e),
                "provider_id": provider_id
            }
    
    def send_inmail(
        self,
        provider_id: str,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        campaign_num: str,
        custom_subject: Optional[str] = None,
        custom_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a LinkedIn InMail (premium message) to a candidate.
        
        Args:
            provider_id: LinkedIn user ID
            candidate_name: Candidate's first name
            candidate_info: Candidate details
            project_info: Project/job information
            campaign_num: Campaign number
            custom_subject: Optional custom subject
            custom_body: Optional custom body
        
        Returns:
            Report for Outreach Manager
        """
        try:
            logger.info(f"📧 Sending LinkedIn InMail to {provider_id}")
            
            # Generate InMail if not provided
            if not custom_subject or not custom_body:
                subject, body = self._generate_inmail_content(
                    candidate_name, candidate_info, project_info
                )
                custom_subject = custom_subject or subject
                custom_body = custom_body or body
            
            # Execute LinkedIn tool
            tool_result = linkedin_inmail_send(provider_id, custom_subject, custom_body)
            
            if tool_result["status"] != "success":
                raise Exception(tool_result.get("error", "Unknown error"))
            
            # Update Database Agent
            db_result = self.db_agent.tools.update_candidate_status(
                linkedin_url=candidate_info.get("linkedin_url", ""),
                updates={
                    "inmail": True,
                    "inmail_datum": datetime.utcnow().isoformat(),
                    "projectid": project_info["projectid"],
                    "project_naam": project_info["project_name"],
                    "campaign_num": campaign_num,
                    "last_contact": "inmail",
                    "last_contact_date": datetime.utcnow().isoformat()
                }
            )
            
            # Prepare report
            report = {
                "action": "inmail",
                "candidate_name": candidate_name,
                "provider_id": provider_id,
                "subject": custom_subject,
                "linkedin_tool_confirmation": tool_result,
                "database_update_confirmation": db_result,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ InMail sent and logged: {provider_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error sending InMail: {e}")
            return {
                "action": "inmail",
                "status": "error",
                "error": str(e),
                "provider_id": provider_id
            }
    
    def like_candidate_post(
        self,
        post_id: str,
        provider_id: str,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        campaign_num: str
    ) -> Dict[str, Any]:
        """
        Like a LinkedIn post from a candidate to engage with them.
        
        Args:
            post_id: LinkedIn post ID
            provider_id: LinkedIn user ID
            candidate_name: Candidate's first name
            candidate_info: Candidate details
            project_info: Project/job information
            campaign_num: Campaign number
        
        Returns:
            Report for Outreach Manager
        """
        try:
            logger.info(f"👍 Liking LinkedIn post {post_id}")
            
            # Execute LinkedIn tool
            tool_result = linkedin_post_reaction_like(post_id)
            
            if tool_result["status"] != "success":
                raise Exception(tool_result.get("error", "Unknown error"))
            
            # Update Database Agent
            db_result = self.db_agent.tools.update_candidate_status(
                linkedin_url=candidate_info.get("linkedin_url", ""),
                updates={
                    "post_geliked": True,
                    "post_geliked_datum": datetime.utcnow().isoformat(),
                    "projectid": project_info["projectid"],
                    "project_naam": project_info["project_name"],
                    "campaign_num": campaign_num,
                    "last_engagement": "post_like",
                    "last_engagement_date": datetime.utcnow().isoformat()
                }
            )
            
            # Prepare report
            report = {
                "action": "post_liked",
                "candidate_name": candidate_name,
                "post_id": post_id,
                "provider_id": provider_id,
                "linkedin_tool_confirmation": tool_result,
                "database_update_confirmation": db_result,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ Post liked and logged: {post_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error liking post: {e}")
            return {
                "action": "post_liked",
                "status": "error",
                "error": str(e),
                "post_id": post_id
            }
    
    def _generate_connection_message(
        self,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any]
    ) -> str:
        """Generate a personalized connection request message."""
        try:
            prompt = LinkedInOutreachPrompts.connection_request_message(
                candidate_name, candidate_info, project_info, self.user_info
            )
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Could not generate message: {e}, using default")
            return f"Hi {candidate_name}, I'd like to connect with you!"
    
    def _generate_linkedin_message(
        self,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any]
    ) -> str:
        """Generate a personalized LinkedIn direct message."""
        try:
            prompt = LinkedInOutreachPrompts.linkedin_message_content(
                candidate_name, candidate_info, project_info, self.user_info
            )
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Could not generate message: {e}, using default")
            return f"Hi {candidate_name}, I came across your profile and think you might be interested in an opportunity."
    
    def _generate_inmail_content(
        self,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any]
    ) -> tuple:
        """Generate InMail subject and body."""
        try:
            prompt = LinkedInOutreachPrompts.inmail_content(
                candidate_name, candidate_info, project_info, self.user_info
            )
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Parse subject and body (assuming format "Subject:\n...\n\nBody:\n...")
            parts = content.split("\n\n", 1)
            subject = parts[0].replace("Subject:", "").strip() if len(parts) > 0 else "Exciting Opportunity"
            body = parts[1] if len(parts) > 1 else content
            
            return subject, body
        except Exception as e:
            logger.warning(f"Could not generate InMail: {e}, using default")
            return "New Opportunity", f"Hi {candidate_name}, I think you might be interested in a new opportunity."


# Example usage
if __name__ == "__main__":
    user_info = {
        "voornaam": "Carlos",
        "bedrijfsnaam": "Talent Solutions",
        "functietitel": "Senior Recruitment Consultant"
    }
    
    agent = LinkedInOutreachAgent(user_info)
    
    candidate_info = {
        "naam": "John",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "current_position": "Senior Developer",
        "skills": ["Python", "Django"]
    }
    
    project_info = {
        "projectid": "PROJ-2025-001",
        "project_name": "Lead Python Developer at InnovateTech",
        "functie": "Lead Python Developer"
    }
    
    # Send connection request
    result = agent.send_connection_request(
        provider_id="john-doe-123",
        candidate_name="John",
        candidate_info=candidate_info,
        project_info=project_info,
        campaign_num="CAMP-2025-01"
    )
    
    print("Connection Request Result:")
    print(result)