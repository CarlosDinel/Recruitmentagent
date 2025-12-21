"""Outreach use cases."""

from .send_email_outreach import (
    SendEmailOutreachUseCase,
    SendEmailOutreachRequest,
    SendEmailOutreachResponse
)
from .send_linkedin_outreach import (
    SendLinkedInOutreachUseCase,
    SendLinkedInOutreachRequest,
    SendLinkedInOutreachResponse
)
from .generate_personalized_message import (
    GeneratePersonalizedMessageUseCase,
    GeneratePersonalizedMessageRequest,
    GeneratePersonalizedMessageResponse
)

__all__ = [
    'SendEmailOutreachUseCase',
    'SendEmailOutreachRequest',
    'SendEmailOutreachResponse',
    'SendLinkedInOutreachUseCase',
    'SendLinkedInOutreachRequest',
    'SendLinkedInOutreachResponse',
    'GeneratePersonalizedMessageUseCase',
    'GeneratePersonalizedMessageRequest',
    'GeneratePersonalizedMessageResponse',
]

