"""Validation Error Exception"""

from typing import Dict, List, Any


class ValidationError(Exception):
    """Raised when entity validation fails."""
    
    def __init__(self, field: str = None, message: str = None, errors: Dict[str, List[str]] = None):
        self.field = field
        self.errors = errors or {}
        
        if message:
            self.message = message
        elif field:
            self.message = f"Validation failed for field: {field}"
        elif errors:
            self.message = f"Validation failed: {self._format_errors(errors)}"
        else:
            self.message = "Validation failed"
        
        super().__init__(self.message)
    
    @staticmethod
    def _format_errors(errors: Dict[str, List[str]]) -> str:
        """Format multiple validation errors."""
        formatted = []
        for field, messages in errors.items():
            formatted.append(f"{field}: {', '.join(messages)}")
        return "; ".join(formatted)
