"""Deduplication Service - Domain Logic"""

from typing import List, Set, Optional
from ..entities import Candidate
from ..value_objects import CandidateId


class DeduplicationService:
    """
    Domain service for candidate deduplication.
    Pure business logic with no external dependencies.
    """
    
    @staticmethod
    def find_duplicates_by_linkedin(candidates: List[Candidate]) -> List[List[Candidate]]:
        """
        Find duplicate candidates by LinkedIn URL.
        
        Args:
            candidates: List of candidates to check
            
        Returns:
            List of duplicate groups (each group contains duplicate candidates)
        """
        linkedin_map: dict[str, List[Candidate]] = {}
        
        for candidate in candidates:
            linkedin_url = candidate.contact_info.linkedin_url
            if linkedin_url:
                normalized_url = DeduplicationService._normalize_linkedin_url(linkedin_url)
                if normalized_url not in linkedin_map:
                    linkedin_map[normalized_url] = []
                linkedin_map[normalized_url].append(candidate)
        
        # Return only groups with duplicates
        return [group for group in linkedin_map.values() if len(group) > 1]
    
    @staticmethod
    def find_duplicates_by_email(candidates: List[Candidate]) -> List[List[Candidate]]:
        """
        Find duplicate candidates by email.
        
        Args:
            candidates: List of candidates to check
            
        Returns:
            List of duplicate groups
        """
        email_map: dict[str, List[Candidate]] = {}
        
        for candidate in candidates:
            email = candidate.contact_info.email
            if email:
                normalized_email = email.strip().lower()
                if normalized_email not in email_map:
                    email_map[normalized_email] = []
                email_map[normalized_email].append(candidate)
        
        return [group for group in email_map.values() if len(group) > 1]
    
    @staticmethod
    def find_duplicates_by_name(candidates: List[Candidate]) -> List[List[Candidate]]:
        """
        Find potential duplicate candidates by name similarity.
        This is less reliable than LinkedIn/email matching.
        
        Args:
            candidates: List of candidates to check
            
        Returns:
            List of potential duplicate groups
        """
        name_map: dict[str, List[Candidate]] = {}
        
        for candidate in candidates:
            normalized_name = DeduplicationService._normalize_name(candidate.name)
            if normalized_name not in name_map:
                name_map[normalized_name] = []
            name_map[normalized_name].append(candidate)
        
        return [group for group in name_map.values() if len(group) > 1]
    
    @staticmethod
    def is_duplicate(candidate1: Candidate, candidate2: Candidate) -> bool:
        """
        Check if two candidates are duplicates.
        
        Args:
            candidate1: First candidate
            candidate2: Second candidate
            
        Returns:
            True if candidates are duplicates
        """
        # Check LinkedIn URL (strongest signal)
        if candidate1.contact_info.linkedin_url and candidate2.contact_info.linkedin_url:
            url1 = DeduplicationService._normalize_linkedin_url(candidate1.contact_info.linkedin_url)
            url2 = DeduplicationService._normalize_linkedin_url(candidate2.contact_info.linkedin_url)
            if url1 == url2:
                return True
        
        # Check email
        if candidate1.contact_info.email and candidate2.contact_info.email:
            email1 = candidate1.contact_info.email.strip().lower()
            email2 = candidate2.contact_info.email.strip().lower()
            if email1 == email2:
                return True
        
        # Check name + company combination (weaker signal)
        if candidate1.name and candidate2.name and candidate1.current_company and candidate2.current_company:
            name1 = DeduplicationService._normalize_name(candidate1.name)
            name2 = DeduplicationService._normalize_name(candidate2.name)
            company1 = candidate1.current_company.strip().lower()
            company2 = candidate2.current_company.strip().lower()
            
            if name1 == name2 and company1 == company2:
                return True
        
        return False
    
    @staticmethod
    def remove_duplicates(candidates: List[Candidate]) -> List[Candidate]:
        """
        Remove duplicate candidates from list, keeping the first occurrence.
        
        Args:
            candidates: List of candidates
            
        Returns:
            List with duplicates removed
        """
        unique_candidates = []
        seen_linkedin: Set[str] = set()
        seen_emails: Set[str] = set()
        seen_ids: Set[str] = set()
        
        for candidate in candidates:
            # Check by ID first
            candidate_id_str = str(candidate.id)
            if candidate_id_str in seen_ids:
                continue
            
            # Check by LinkedIn URL
            if candidate.contact_info.linkedin_url:
                linkedin_url = DeduplicationService._normalize_linkedin_url(
                    candidate.contact_info.linkedin_url
                )
                if linkedin_url in seen_linkedin:
                    continue
                seen_linkedin.add(linkedin_url)
            
            # Check by email
            if candidate.contact_info.email:
                email = candidate.contact_info.email.strip().lower()
                if email in seen_emails:
                    continue
                seen_emails.add(email)
            
            seen_ids.add(candidate_id_str)
            unique_candidates.append(candidate)
        
        return unique_candidates
    
    @staticmethod
    def merge_candidate_data(primary: Candidate, secondary: Candidate) -> Candidate:
        """
        Merge data from two duplicate candidates, keeping primary as base.
        
        Args:
            primary: Primary candidate (will be updated)
            secondary: Secondary candidate (data source)
            
        Returns:
            Updated primary candidate with merged data
        """
        # Merge profile data
        merged_profile = {**primary.profile_data, **secondary.profile_data}
        primary.enrich_profile(merged_profile)
        
        # Update skills if secondary has more
        if len(secondary.skills) > len(primary.skills):
            all_skills = list(primary.skills.skills) + list(secondary.skills.skills)
            # This would require making skills mutable or creating new Candidate
            # For now, just add to profile data
            primary.profile_data['additional_skills'] = list(secondary.skills.skills)
        
        # Keep better evaluation score
        if secondary.evaluation_score and primary.evaluation_score:
            if secondary.evaluation_score.overall_score > primary.evaluation_score.overall_score:
                primary.evaluate(secondary.evaluation_score)
        elif secondary.evaluation_score:
            primary.evaluate(secondary.evaluation_score)
        
        return primary
    
    @staticmethod
    def _normalize_linkedin_url(url: str) -> str:
        """Normalize LinkedIn URL for comparison."""
        # Remove trailing slash, http/https, www
        normalized = url.strip().lower()
        normalized = normalized.rstrip('/')
        normalized = normalized.replace('https://', '').replace('http://', '')
        normalized = normalized.replace('www.', '')
        return normalized
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize name for comparison."""
        # Convert to lowercase, remove extra whitespace, remove common titles
        normalized = name.strip().lower()
        normalized = ' '.join(normalized.split())
        
        # Remove common titles
        titles = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'ir.', 'drs.', 'msc', 'bsc']
        for title in titles:
            normalized = normalized.replace(title, '').strip()
        
        return normalized
