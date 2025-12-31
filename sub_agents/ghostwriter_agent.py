"""
Ghostwriter Agent - Writes messages and emails in the user's recruitment style.
This agent specializes in writing personalized recruitment messages for LinkedIn and email.
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Local imports - none needed, prompts embedded

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GhostwriterPrompts:
    """Embedded prompts for ghostwriter message generation."""
    
    @staticmethod
    def system_prompt(user_info: Dict[str, Any]) -> str:
        voornaam = user_info.get('voornaam', 'recruiter')
        bedrijf = user_info.get('bedrijfsnaam', 'recruitment team')
        return (
            f"You are writing recruitment messages for {voornaam} from {bedrijf}. "
            f"Style: professional yet warm, direct, personal (use first names), short sentences, max 150 words for LinkedIn. "
            f"Sign off: Met vriendelijke groet,\\n{voornaam}\\n{user_info.get('functietitel', 'Recruitment Consultant')}"
        )
    
    @staticmethod
    def write_first_message_prompt(candidate_name: str, candidate_info: Dict[str, Any], job_info: Dict[str, Any], user_info: Dict[str, Any]) -> str:
        return (
            f"Write FIRST LinkedIn outreach to {candidate_name}.\n"
            f"Role: {candidate_info.get('current_position', 'Unknown')} at {candidate_info.get('current_company', 'Unknown')}\n"
            f"Skills: {', '.join(candidate_info.get('skills', []))}\n"
            f"Vacancy: {job_info.get('job_title', 'Unknown')} at {job_info.get('company_name', 'Unknown')}\n"
            f"Max 150 words. Connect their experience to role, be specific, end with friendly call to chat."
        )
    
    @staticmethod
    def write_follow_up_message_prompt(candidate_name: str, candidate_info: Dict[str, Any], conversation_history: str, message_type: str, user_info: Dict[str, Any]) -> str:
        return (
            f"Write FOLLOW-UP message to {candidate_name}.\n"
            f"History: {conversation_history}\n"
            f"Type: {message_type}\n"
            f"Max 100 words. Respond to their last message, keep it relevant, clear CTA."
        )
    
    @staticmethod
    def write_meeting_invite_prompt(candidate_name: str, meeting_options: list, context: str, user_info: Dict[str, Any]) -> str:
        opts = '\\n'.join([f"- {o}" for o in meeting_options])
        return (
            f"Write MEETING INVITE to {candidate_name}.\n"
            f"Context: {context}\n"
            f"Options:\\n{opts}\n"
            f"Max 80 words. Reference conversation, propose times, make it easy to choose."
        )
    
    @staticmethod
    def write_rejection_graceful_prompt(candidate_name: str, reason: Optional[str], user_info: Dict[str, Any]) -> str:
        return (
            f"Write graceful CLOSING message to {candidate_name} (not interested).\n"
            f"Reason: {reason or 'Not given'}\n"
            f"Max 50 words. Accept with understanding, leave door open, wish them well."
        )
    
    @staticmethod
    def adapt_tone_for_sector_prompt(message_draft: str, sector: str) -> str:
        return (
            f"Adapt tone for {sector} sector:\\n{message_draft}\n"
            f"Keep core message, adjust formality/style for {sector}. Same length."
        )

def get_ghostwriter_config(user_info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_info": user_info,
        "max_message_length": {"first_message": 150, "follow_up": 100, "meeting_invite": 80, "graceful_rejection": 50},
        "signature_format": f"Met vriendelijke groet,\\n{user_info.get('voornaam', 'Recruiter')}\\n{user_info.get('functietitel', 'Recruitment Consultant')}"
    }



class GhostwriterAgent:
    """
    Agent that writes recruitment messages in the user's personal style.
    
    Responsibilities:
    - Write first outreach messages for candidates
    - Write follow-up messages based on conversation history
    - Write meeting invitation messages
    - Handle graceful rejections
    - Adapt tone for different sectors (horeca, tech, finance, etc.)
    
    This agent is instructed by the Outreach Manager.
    """
    
    def __init__(self, user_info: Dict[str, Any], llm_provider: str = "openai"):
        """
        Initialize the Ghostwriter Agent.
        
        Args:
            user_info: Dictionary containing user context (voornaam, bedrijfsnaam, functietitel, context)
            llm_provider: AI provider to use ("openai" or "anthropic")
        """
        self.user_info = user_info
        self.config = get_ghostwriter_config(user_info)
        self.llm_provider = llm_provider
        
        # Initialize LLM
        if llm_provider == "openai":
            self.llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-5"),
                temperature=0.7,  # Creative but consistent
                api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            self.llm = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                temperature=0.7,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        
        logger.info(f"✅ GhostwriterAgent initialized for {user_info.get('voornaam', 'user')} using {llm_provider}")
    
    def write_first_message(
        self,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        job_info: Dict[str, Any],
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write the first outreach message to a candidate.
        
        Args:
            candidate_name: First name of the candidate
            candidate_info: Dictionary with candidate details (position, company, skills, etc.)
            job_info: Dictionary with job details (company, title, description, skills)
            sector: Optional sector for tone adaptation (horeca, tech, finance, etc.)
        
        Returns:
            Dictionary with message text, metadata, and word count
        """
        try:
            logger.info(f"📝 Writing first message for {candidate_name}")
            
            # Generate system prompt with user context
            system_prompt = GhostwriterPrompts.system_prompt(self.user_info)
            
            # Generate task-specific prompt
            task_prompt = GhostwriterPrompts.write_first_message_prompt(
                candidate_name=candidate_name,
                candidate_info=candidate_info,
                job_info=job_info,
                user_info=self.user_info
            )
            
            # Generate message
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task_prompt)
            ]
            
            response = self.llm.invoke(messages)
            message_text = response.content.strip()
            
            # Adapt tone if sector specified
            if sector:
                message_text = self._adapt_tone_for_sector(message_text, sector)
            
            # Validate message length
            word_count = len(message_text.split())
            max_words = self.config["max_message_length"]["first_message"]
            
            if word_count > max_words:
                logger.warning(f"⚠️ Message exceeds {max_words} words ({word_count} words), considering shortening")
            
            result = {
                "message": message_text,
                "candidate_name": candidate_name,
                "message_type": "first_message",
                "word_count": word_count,
                "sector": sector,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ First message written ({word_count} words)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error writing first message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": None
            }
    
    def write_follow_up(
        self,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        conversation_history: str,
        message_type: str = "general_follow_up"
    ) -> Dict[str, Any]:
        """
        Write a follow-up message based on conversation history.
        
        Args:
            candidate_name: First name of the candidate
            candidate_info: Dictionary with candidate details
            conversation_history: String with previous conversation
            message_type: Type of follow-up (general_follow_up, after_no_response, etc.)
        
        Returns:
            Dictionary with message text and metadata
        """
        try:
            logger.info(f"📝 Writing follow-up message for {candidate_name}")
            
            system_prompt = GhostwriterPrompts.system_prompt(self.user_info)
            task_prompt = GhostwriterPrompts.write_follow_up_message_prompt(
                candidate_name=candidate_name,
                candidate_info=candidate_info,
                conversation_history=conversation_history,
                message_type=message_type,
                user_info=self.user_info
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task_prompt)
            ]
            
            response = self.llm.invoke(messages)
            message_text = response.content.strip()
            
            word_count = len(message_text.split())
            
            result = {
                "message": message_text,
                "candidate_name": candidate_name,
                "message_type": f"follow_up_{message_type}",
                "word_count": word_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ Follow-up message written ({word_count} words)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error writing follow-up: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": None
            }
    
    def write_meeting_invite(
        self,
        candidate_name: str,
        meeting_options: List[str],
        context: str
    ) -> Dict[str, Any]:
        """
        Write a meeting invitation with specific time options.
        
        Args:
            candidate_name: First name of the candidate
            meeting_options: List of available meeting times
            context: Context of the conversation so far
        
        Returns:
            Dictionary with invitation message and metadata
        """
        try:
            logger.info(f"📅 Writing meeting invite for {candidate_name}")
            
            system_prompt = GhostwriterPrompts.system_prompt(self.user_info)
            task_prompt = GhostwriterPrompts.write_meeting_invite_prompt(
                candidate_name=candidate_name,
                meeting_options=meeting_options,
                context=context,
                user_info=self.user_info
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task_prompt)
            ]
            
            response = self.llm.invoke(messages)
            message_text = response.content.strip()
            
            result = {
                "message": message_text,
                "candidate_name": candidate_name,
                "message_type": "meeting_invite",
                "meeting_options": meeting_options,
                "word_count": len(message_text.split()),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ Meeting invite written")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error writing meeting invite: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": None
            }
    
    def write_graceful_rejection(
        self,
        candidate_name: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write a graceful closing message when candidate is not interested.
        
        Args:
            candidate_name: First name of the candidate
            reason: Optional reason why candidate is not interested
        
        Returns:
            Dictionary with closing message and metadata
        """
        try:
            logger.info(f"👋 Writing graceful rejection for {candidate_name}")
            
            system_prompt = GhostwriterPrompts.system_prompt(self.user_info)
            task_prompt = GhostwriterPrompts.write_rejection_graceful_prompt(
                candidate_name=candidate_name,
                reason=reason,
                user_info=self.user_info
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task_prompt)
            ]
            
            response = self.llm.invoke(messages)
            message_text = response.content.strip()
            
            result = {
                "message": message_text,
                "candidate_name": candidate_name,
                "message_type": "graceful_rejection",
                "reason": reason,
                "word_count": len(message_text.split()),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            logger.info(f"✅ Graceful rejection written")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error writing rejection: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": None
            }
    
    def _adapt_tone_for_sector(self, message_draft: str, sector: str) -> str:
        """
        Adapt the tone of a message for a specific sector.
        
        Args:
            message_draft: Original message text
            sector: Target sector (horeca, tech, finance, executive, etc.)
        
        Returns:
            Adapted message text
        """
        try:
            logger.info(f"🎨 Adapting tone for {sector} sector")
            
            task_prompt = GhostwriterPrompts.adapt_tone_for_sector_prompt(
                message_draft=message_draft,
                sector=sector
            )
            
            response = self.llm.invoke([HumanMessage(content=task_prompt)])
            adapted_message = response.content.strip()
            
            logger.info(f"✅ Tone adapted for {sector}")
            return adapted_message
            
        except Exception as e:
            logger.warning(f"⚠️ Could not adapt tone: {e}, returning original")
            return message_draft
    
    def batch_write_messages(
        self,
        candidates: List[Dict[str, Any]],
        job_info: Dict[str, Any],
        message_type: str = "first_message",
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write messages for multiple candidates in batch.
        
        Args:
            candidates: List of candidate dictionaries with name and info
            job_info: Job information for all candidates
            message_type: Type of message to write
            sector: Optional sector for tone adaptation
        
        Returns:
            Dictionary with results for all candidates
        """
        logger.info(f"📝 Batch writing {len(candidates)} {message_type} messages")
        
        results = {
            "total": len(candidates),
            "successful": 0,
            "failed": 0,
            "messages": []
        }
        
        for candidate in candidates:
            try:
                if message_type == "first_message":
                    result = self.write_first_message(
                        candidate_name=candidate["name"],
                        candidate_info=candidate["info"],
                        job_info=job_info,
                        sector=sector
                    )
                else:
                    result = self.write_follow_up(
                        candidate_name=candidate["name"],
                        candidate_info=candidate["info"],
                        conversation_history=candidate.get("history", ""),
                        message_type=message_type
                    )
                
                if result["status"] == "success":
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                
                results["messages"].append(result)
                
            except Exception as e:
                logger.error(f"❌ Error processing {candidate['name']}: {e}")
                results["failed"] += 1
                results["messages"].append({
                    "candidate_name": candidate["name"],
                    "status": "error",
                    "error": str(e)
                })
        
        logger.info(f"✅ Batch complete: {results['successful']} successful, {results['failed']} failed")
        return results
    
    def get_signature(self) -> str:
        """Get the user's signature for messages."""
        return self.config["signature_format"]
    
    def validate_message_quality(self, message: str) -> Dict[str, Any]:
        """
        Validate the quality of a generated message.
        
        Checks:
        - Length within limits
        - Contains candidate name
        - Has proper structure
        - Ends with signature
        
        Returns:
            Dictionary with validation results
        """
        word_count = len(message.split())
        
        validation = {
            "valid": True,
            "issues": [],
            "word_count": word_count,
            "warnings": []
        }
        
        # Check length
        if word_count > 200:
            validation["warnings"].append(f"Message is long ({word_count} words)")
        
        # Check signature
        if self.user_info["voornaam"] not in message:
            validation["issues"].append("Missing signature with user name")
            validation["valid"] = False
        
        # Check structure (paragraphs)
        if "\n\n" not in message:
            validation["warnings"].append("Message has no paragraph breaks")
        
        return validation


# Factory function for easy instantiation
def create_ghostwriter_agent(
    voornaam: str,
    bedrijfsnaam: str,
    functietitel: str = "Recruitment Consultant",
    context: str = "We helpen bedrijven de juiste talenten te vinden.",
    llm_provider: str = "openai"
) -> GhostwriterAgent:
    """
    Factory function to create a GhostwriterAgent with user configuration.
    
    Args:
        voornaam: First name of the user/recruiter
        bedrijfsnaam: Company name
        functietitel: Job title of the user
        context: Company/user context description
        llm_provider: AI provider ("openai" or "anthropic")
    
    Returns:
        Configured GhostwriterAgent instance
    """
    user_info = {
        "voornaam": voornaam,
        "bedrijfsnaam": bedrijfsnaam,
        "functietitel": functietitel,
        "context": context
    }
    
    return GhostwriterAgent(user_info=user_info, llm_provider=llm_provider)


# Example usage
if __name__ == "__main__":
    # Example: Create agent for a recruiter
    agent = create_ghostwriter_agent(
        voornaam="Carlos",
        bedrijfsnaam="Talent Solutions",
        functietitel="Senior Recruitment Consultant",
        context="We zijn gespecialiseerd in recruitment voor de tech sector en helpen innovatieve bedrijven de beste tech talenten te vinden."
    )
    
    # Example candidate and job info
    candidate_info = {
        "current_position": "Senior Python Developer",
        "current_company": "TechCorp",
        "years_experience": 5,
        "skills": ["Python", "Django", "PostgreSQL", "Docker"],
        "location": "Amsterdam",
        "open_to_work": True
    }
    
    job_info = {
        "company_name": "InnovateTech BV",
        "job_title": "Lead Python Developer",
        "location": "Amsterdam",
        "description": "We zoeken een ervaren Python developer die ons team kan versterken",
        "required_skills": ["Python", "Django", "PostgreSQL", "Team leadership"]
    }
    
    # Write first message
    result = agent.write_first_message(
        candidate_name="John",
        candidate_info=candidate_info,
        job_info=job_info,
        sector="tech"
    )
    
    if result["status"] == "success":
        print("=" * 60)
        print("GENERATED MESSAGE:")
        print("=" * 60)
        print(result["message"])
        print("=" * 60)
        print(f"Word count: {result['word_count']}")
        print(f"Sector: {result['sector']}")
    else:
        print(f"Error: {result['error']}")