"""Candidate Not Found Exception"""


class CandidateNotFound(Exception):
    """Raised when a candidate cannot be found."""
    
    def __init__(self, candidate_id: str, message: str = None):
        self.candidate_id = candidate_id
        self.message = message or f"Candidate not found: {candidate_id}"
        super().__init__(self.message)
