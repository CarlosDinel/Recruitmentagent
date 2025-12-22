"""
Prompts for the LinkedIn Outreach Agent
Generates personalized messages for connection requests, direct messages, and InMails.
"""

from typing import Dict, Any


class LinkedInOutreachPrompts:
    """Prompts for generating LinkedIn outreach messages."""
    
    @staticmethod
    def connection_request_message(
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        user_info: Dict[str, Any]
    ) -> str:
        """Generate a personalized connection request message."""
        return f"""
Schrijf een persoonlijk LinkedIn connection request message voor {candidate_name}.

KANDIDAAT INFO:
- Naam: {candidate_name}
- Huidige functie: {candidate_info.get('current_position', 'Unknown')}
- Bedrijf: {candidate_info.get('company', 'Unknown')}
- Skills: {', '.join(candidate_info.get('skills', []))}

VACATURE INFO:
- Project: {project_info['project_name']}
- Functie: {project_info.get('functie', 'Unknown')}

JOUW INFO:
- Naam: {user_info['voornaam']}
- Bedrijf: {user_info['bedrijfsnaam']}

REGELS:
- Korte, persoonlijke boodschap (max 300 karakters)
- Verwijs naar gemeenschappelijke interesse of skills
- Wees warm en vriendelijk
- Geen sales pitch, gewoon genuine interesse tonen

Schrijf nu het connection request message:
"""
    
    @staticmethod
    def linkedin_message_content(
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        user_info: Dict[str, Any]
    ) -> str:
        """Generate a personalized LinkedIn direct message."""
        return f"""
Schrijf een persoonlijk LinkedIn direct message voor {candidate_name}.

KANDIDAAT INFO:
- Naam: {candidate_name}
- Huidige functie: {candidate_info.get('current_position', 'Unknown')}
- Ervaring: {candidate_info.get('years_experience', 'Unknown')} jaar
- Skills: {', '.join(candidate_info.get('skills', []))}

VACATURE INFO:
- Project: {project_info['project_name']}
- Functie: {project_info.get('functie', 'Unknown')}
- Bedrijf: {project_info.get('company', 'Unknown')}

JOUW INFO:
- Naam: {user_info['voornaam']}
- Titel: {user_info.get('functietitel', 'Recruitment Consultant')}

REGELS:
- Direct, interessant, en relevant (max 500 karakters)
- Begin met persoonlijke observatie over hun profiel
- Verwijs naar specifieke skills/ervaring die matchen
- Eindig met vriendelijke vraag of voorstel
- Tone: Professioneel maar warm en menselijk

Schrijf nu het LinkedIn direct message:
"""
    
    @staticmethod
    def inmail_content(
        candidate_name: str,
        candidate_info: Dict[str, Any],
        project_info: Dict[str, Any],
        user_info: Dict[str, Any]
    ) -> str:
        """Generate LinkedIn InMail subject and body."""
        return f"""
Schrijf een LinkedIn InMail (premium message) voor {candidate_name}.

KANDIDAAT INFO:
- Naam: {candidate_name}
- Huidige functie: {candidate_info.get('current_position', 'Unknown')}
- Ervaring: {candidate_info.get('years_experience', 'Unknown')} jaar
- Skills: {', '.join(candidate_info.get('skills', []))}

VACATURE INFO:
- Project: {project_info['project_name']}
- Functie: {project_info.get('functie', 'Unknown')}
- Bedrijf: {project_info.get('company', 'Unknown')}

JOUW INFO:
- Naam: {user_info['voornaam']}
- Titel: {user_info.get('functietitel', 'Recruitment Consultant')}

FORMAT:
Subject: [Korte, aantrekkelijke subject line, max 50 karakters]

Body: [Uitgebreider bericht, max 1000 karakters]

REGELS VOOR SUBJECT:
- Aantrekkelijk en duidelijk
- Verwijs naar voordeel voor kandidaat
- Geen clickbait

REGELS VOOR BODY:
- Warme persoonlijke opening met voornaam
- Duidelijke reden waarom deze kans relevant is
- Specifieke match tussen skills/ervaring en rol
- Korte beschrijving van bedrijf en rol
- Duidelijke call-to-action
- Warm, professioneel, menselijk
- Proper signing met naam en titel

Schrijf nu de InMail:
"""