"""Use cases - application-specific business rules."""

from .sourcing import (
    SearchCandidatesUseCase,
    EvaluateCandidatesUseCase,
    EnrichCandidateProfilesUseCase
)
from .outreach import (
    SendEmailOutreachUseCase,
    SendLinkedInOutreachUseCase,
    GeneratePersonalizedMessageUseCase
)

__all__ = [
    # Sourcing
    'SearchCandidatesUseCase',
    'EvaluateCandidatesUseCase',
    'EnrichCandidateProfilesUseCase',
    # Outreach
    'SendEmailOutreachUseCase',
    'SendLinkedInOutreachUseCase',
    'GeneratePersonalizedMessageUseCase',
]

