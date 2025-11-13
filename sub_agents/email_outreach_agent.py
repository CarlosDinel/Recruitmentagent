"""This module defines the Email Outreach Agent responsible for generating and sending outreach emails.

"""

from datetime import datetime
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from tools.outreach_tools import send_outreach_email
from agents.database_agent import DatabaseAgent
from prompts.outreach_manager_prompts import generate_email_prompt

class EmailOutreachAgent:
    """
    Agent that generates and sends personalized outreach emails,
    and records each contact moment in the Database Agent.
    """

    def __init__(self, user_info: Dict[str, Any], ai_model: str = "gpt-4"):
        self.user_info = user_info
        self.llm = ChatOpenAI(model_name=ai_model)
        self.db_agent = DatabaseAgent()

    def generate_email_text(
        self,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any]
    ) -> str:
        """Generate a personalized email using an AI prompt."""
        system_prompt = "Je bent een recruitment consultant. Schrijf een persoonlijk, relevant en professioneel mailbericht voor een kandidaat."
        prompt = generate_email_prompt(candidate_info, project_info, self.user_info)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content.strip()

    def send_and_record_email(
        self,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        campaign_num: str
    ) -> Dict[str, Any]:
        """
        Generate, send, and record an outreach email.
        """
        recipient_email = candidate_info["email"]
        recipient_name = candidate_info["naam"]
        subject = f"Kans bij {project_info['project_name']}"
        body = self.generate_email_text(candidate_info, project_info)

        # 1. Send the email
        email_tool_result = send_outreach_email(recipient_email, subject, body)

        # 2. Update the database agent
        db_update_result = self.db_agent.update_candidate_contact(
            recipient_email=recipient_email,
            contact_type="email",
            contact_status=True,
            contact_date=datetime.utcnow().isoformat(),
            projectid=project_info["projectid"],
            project_name=project_info["project_name"],
            campaign_num=campaign_num
        )

        # 3. Prepare output for Outreach Manager
        report = {
            "recipient": recipient_name,
            "subject": subject,
            "email_body": body,
            "email_tool_confirmation": email_tool_result,
            "database_update_confirmation": db_update_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        return report

# Voorbeeld van een prompt in outreach_manager_prompts.py:
def generate_email_prompt(candidate_info, project_info, user_info):
    return (
        f"Beste {candidate_info['naam']},\n\n"
        f"Ik zag je profiel en denk dat je goed past bij onze rol als {project_info['functie']} bij {project_info['project_name']}.\n"
        f"Je ervaring bij {candidate_info.get('huidig_bedrijf', '')} en je skills ({', '.join(candidate_info.get('skills', []))}) sluiten mooi aan.\n"
        f"Kunnen we binnenkort bellen om de mogelijkheden te bespreken?\n\n"
        f"Met vriendelijke groet,\n{user_info['voornaam']}\n{user_info['functietitel']}"
    )