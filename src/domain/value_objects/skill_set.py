"""Skill Set Value Object"""

from dataclasses import dataclass
from typing import List, Set, FrozenSet


@dataclass(frozen=True)
class SkillSet:
    """Immutable set of skills."""
    
    skills: FrozenSet[str]
    
    def __init__(self, skills: List[str]):
        """Initialize with list of skills."""
        # Normalize: lowercase, strip whitespace, remove duplicates
        normalized = frozenset(s.strip().lower() for s in skills if s and s.strip())
        object.__setattr__(self, 'skills', normalized)
    
    def contains(self, skill: str) -> bool:
        """Check if skill set contains a specific skill."""
        return skill.strip().lower() in self.skills
    
    def contains_any(self, skills: List[str]) -> bool:
        """Check if skill set contains any of the given skills."""
        normalized = {s.strip().lower() for s in skills if s and s.strip()}
        return bool(self.skills & normalized)
    
    def contains_all(self, skills: List[str]) -> bool:
        """Check if skill set contains all of the given skills."""
        normalized = {s.strip().lower() for s in skills if s and s.strip()}
        return normalized.issubset(self.skills)
    
    def match_score(self, required_skills: 'SkillSet') -> float:
        """Calculate match score (0.0 to 1.0) against required skills."""
        if not required_skills.skills:
            return 1.0
        
        matched = self.skills & required_skills.skills
        return len(matched) / len(required_skills.skills)
    
    def to_list(self) -> List[str]:
        """Convert to sorted list."""
        return sorted(list(self.skills))
    
    def __len__(self) -> int:
        return len(self.skills)
    
    def __str__(self) -> str:
        return f"SkillSet({', '.join(sorted(self.skills))})"
    
    def __repr__(self) -> str:
        return f"SkillSet({self.to_list()})"
