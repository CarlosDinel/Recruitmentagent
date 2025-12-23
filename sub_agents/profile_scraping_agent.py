"""
Profile Scraping Agent - Deep LinkedIn profile enrichment.

This agent is a sub-agent of the sourcing_manager.py agent. It is responsible for getting more 
detailed profiles out of the candidates that have been ingested by the candidate_searching_agent.py. 
The agent utilizes various tools and APIs to scrape detailed profile information from LinkedIn, 
ensuring that comprehensive data is available for further evaluation and decision-making in the 
recruitment process. This agent also updates existing candidate profiles with newly scraped 
information to maintain data accuracy and relevance. Updates will be stored by the database_agent.py.
"""

#  ---- Package imports ----
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import time

#  ---- Local imports ----
from tools.scourcing_tools import LinkedIn_profile_scrape

# Set up logging
logger = logging.getLogger(__name__)


class ProfileScrapingAgent:
    """
    Profile Scraping Agent - Deep LinkedIn profile enrichment specialist.
    
    Role: Detailed LinkedIn profile scraping and enrichment
    Responsibilities:
    - Receive high-priority candidates from Candidate Evaluation Agent (via Sourcing Manager)
    - Scrape detailed LinkedIn profiles for selected candidates
    - Extract work history, education, certifications, skills, and endorsements
    - Update candidate records with enriched data
    - Forward enriched profiles to Database Agent
    - Implement caching to avoid re-scraping
    """
    
    def __init__(self):
        self.name = "Profile Scraping Agent"
        self.role = "Detailed LinkedIn profile scraping and enrichment"
        
        # Scraping configuration
        self.config = {
            "max_retries": 3,
            "retry_delay": 2,  # seconds
            "rate_limit_delay": 1,  # seconds between requests
            "batch_size": 10,  # process in batches to manage rate limits
            "enable_caching": True
        }
        
        # Cached profiles (simple in-memory cache)
        self._profile_cache = {}
    
    def enrich_candidates(
        self,
        sourcing_manager_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point for profile enrichment from Sourcing Manager.
        
        Args:
            sourcing_manager_request: Contains:
                - candidates: List of candidates to enrich (from Evaluation Agent)
                - project_metadata: projectid, naam_project, campaign_num
                - enrichment_config: Optional scraping configuration
                
        Returns:
            Enriched candidate profiles with detailed LinkedIn data
        """
        logger.info(f"🔍 {self.name} enriching candidates for project {sourcing_manager_request.get('projectid', 'unknown')}")
        
        try:
            # Extract input data
            candidates = sourcing_manager_request.get("candidates", [])
            project_metadata = self._extract_project_metadata(sourcing_manager_request)
            enrichment_config = sourcing_manager_request.get("enrichment_config", {})
            
            # Validate inputs
            if not candidates:
                raise ValueError("No candidates provided for enrichment")
            
            logger.info(f"📋 Enriching {len(candidates)} candidate profiles")
            
            # Merge custom config
            config = {**self.config, **enrichment_config}
            
            # Process candidates in batches
            enriched_candidates = self._process_candidates_in_batches(
                candidates=candidates,
                project_metadata=project_metadata,
                config=config
            )
            
            # Prepare response
            response = self._prepare_enrichment_response(
                enriched_candidates=enriched_candidates,
                project_metadata=project_metadata,
                total_processed=len(candidates)
            )
            
            logger.info(f"✅ Enrichment completed: {len(response['enriched_candidates'])} enriched, {response['enrichment_stats']['failed_count']} failed")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Profile enrichment failed: {e}")
            return self._create_error_response(str(e), sourcing_manager_request)
    
    def _process_candidates_in_batches(
        self,
        candidates: List[Dict[str, Any]],
        project_metadata: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process candidates in batches to manage rate limits."""
        
        enriched_candidates = []
        batch_size = config.get("batch_size", 10)
        
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(candidates)-1)//batch_size + 1}")
            
            for candidate in batch:
                enriched = self._enrich_single_candidate(candidate, project_metadata, config)
                enriched_candidates.append(enriched)
                
                # Rate limiting between requests
                if config.get("rate_limit_delay", 0) > 0:
                    time.sleep(config["rate_limit_delay"])
        
        return enriched_candidates
    
    def _enrich_single_candidate(
        self,
        candidate: Dict[str, Any],
        project_metadata: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich a single candidate profile with detailed LinkedIn data."""
        
        linkedin_url = candidate.get("linkedin_url") or candidate.get("profile_url")
        
        if not linkedin_url:
            logger.warning(f"⚠️ No LinkedIn URL for candidate {candidate.get('full_name', 'unknown')}")
            return self._mark_enrichment_failed(candidate, "No LinkedIn URL provided")
        
        # Check cache first
        if config.get("enable_caching") and linkedin_url in self._profile_cache:
            logger.info(f"💾 Using cached profile for {linkedin_url}")
            cached_data = self._profile_cache[linkedin_url]
            enriched_candidate = self._merge_enrichment_data(candidate, cached_data, from_cache=True)
            
            # Add project metadata and status
            enriched_candidate["project_metadata"] = project_metadata
            enriched_candidate["enrichment_timestamp"] = datetime.now().isoformat()
            enriched_candidate["enrichment_status"] = "success"
            
            return enriched_candidate
        
        # Attempt to scrape profile
        enrichment_data = self._scrape_linkedin_profile(linkedin_url, config)
        
        if enrichment_data.get("success"):
            # Cache the result
            if config.get("enable_caching"):
                self._profile_cache[linkedin_url] = enrichment_data["profile_data"]
            
            # Merge with candidate data
            enriched_candidate = self._merge_enrichment_data(
                candidate, 
                enrichment_data["profile_data"],
                from_cache=False
            )
            
            # Add project metadata
            enriched_candidate["project_metadata"] = project_metadata
            enriched_candidate["enrichment_timestamp"] = datetime.now().isoformat()
            enriched_candidate["enrichment_status"] = "success"
            
            logger.info(f"✅ Successfully enriched profile: {candidate.get('full_name', 'unknown')}")
            return enriched_candidate
        else:
            logger.warning(f"⚠️ Failed to enrich profile: {candidate.get('full_name', 'unknown')}")
            return self._mark_enrichment_failed(candidate, enrichment_data.get("error", "Unknown error"))
    
    def _scrape_linkedin_profile(
        self,
        linkedin_url: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Scrape detailed LinkedIn profile with retry logic."""
        
        max_retries = config.get("max_retries", 3)
        retry_delay = config.get("retry_delay", 2)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 Scraping LinkedIn profile (attempt {attempt + 1}/{max_retries}): {linkedin_url}")
                
                # Call the LinkedIn profile scraping tool
                result_json = LinkedIn_profile_scrape.invoke({
                    "linkedin_url": linkedin_url
                })
                
                result = json.loads(result_json) if isinstance(result_json, str) else result_json
                
                if result.get("success"):
                    return {
                        "success": True,
                        "profile_data": result.get("profile_data", {})
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.warning(f"⚠️ Scraping failed (attempt {attempt + 1}): {error_msg}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": error_msg
                        }
                        
            except Exception as e:
                logger.error(f"❌ Exception during scraping (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        "success": False,
                        "error": str(e)
                    }
        
        return {
            "success": False,
            "error": "Max retries exceeded"
        }
    
    def _merge_enrichment_data(
        self,
        candidate: Dict[str, Any],
        profile_data: Dict[str, Any],
        from_cache: bool = False
    ) -> Dict[str, Any]:
        """Merge scraped profile data with existing candidate data."""
        
        enriched = candidate.copy()
        
        # Add enrichment source
        enriched["enrichment_source"] = "cache" if from_cache else "live_scrape"
        
        # Merge work experience
        if "work_experience" in profile_data:
            enriched["work_experience"] = profile_data["work_experience"]
        
        # Merge education
        if "education" in profile_data:
            enriched["education"] = profile_data["education"]
        
        # Merge skills
        if "skills" in profile_data:
            # Merge with existing skills, avoiding duplicates
            existing_skills = set(enriched.get("skills", []))
            new_skills = set(profile_data["skills"])
            enriched["skills"] = list(existing_skills.union(new_skills))
        
        # Merge certifications
        if "certifications" in profile_data:
            enriched["certifications"] = profile_data["certifications"]
        
        # Merge languages
        if "languages" in profile_data:
            enriched["languages"] = profile_data["languages"]
        
        # Merge endorsements
        if "endorsements" in profile_data:
            enriched["endorsements"] = profile_data["endorsements"]
        
        # Update profile summary if available
        if "summary" in profile_data and profile_data["summary"]:
            enriched["profile_summary"] = profile_data["summary"]
        
        # Update headline if available
        if "headline" in profile_data and profile_data["headline"]:
            enriched["headline"] = profile_data["headline"]
        
        # Add connection count
        if "connections_count" in profile_data:
            enriched["connections_count"] = profile_data["connections_count"]
        
        return enriched
    
    def _mark_enrichment_failed(
        self,
        candidate: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """Mark a candidate as failed enrichment."""
        
        failed_candidate = candidate.copy()
        failed_candidate["enrichment_status"] = "failed"
        failed_candidate["enrichment_error"] = error_message
        failed_candidate["enrichment_timestamp"] = datetime.now().isoformat()
        
        return failed_candidate
    
    def _extract_project_metadata(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract project metadata from request."""
        return {
            "project_id": request.get("projectid", request.get("project_id", "")),
            "project_name": request.get("naam_project", request.get("project_name", "")),
            "campaign_num": request.get("campaign_num", ""),
            "search_id": request.get("search_id", "")
        }
    
    def _prepare_enrichment_response(
        self,
        enriched_candidates: List[Dict[str, Any]],
        project_metadata: Dict[str, Any],
        total_processed: int
    ) -> Dict[str, Any]:
        """Prepare final enrichment response."""
        
        # Separate successful and failed enrichments
        successful = [c for c in enriched_candidates if c.get("enrichment_status") == "success"]
        failed = [c for c in enriched_candidates if c.get("enrichment_status") == "failed"]
        
        return {
            "success": True,
            "enriched_candidates": successful,
            "failed_enrichments": failed,
            "enrichment_stats": {
                "total_processed": total_processed,
                "success_count": len(successful),
                "failed_count": len(failed),
                "success_rate": len(successful) / total_processed if total_processed > 0 else 0
            },
            "project_metadata": project_metadata,
            "enrichment_timestamp": datetime.now().isoformat()
        }
    
    def _create_error_response(
        self,
        error_message: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create error response."""
        return {
            "success": False,
            "error": error_message,
            "enriched_candidates": [],
            "failed_enrichments": [],
            "enrichment_stats": {
                "total_processed": 0,
                "success_count": 0,
                "failed_count": 0,
                "success_rate": 0.0
            },
            "project_metadata": self._extract_project_metadata(request),
            "enrichment_timestamp": datetime.now().isoformat()
        }
    
    def clear_cache(self):
        """Clear the profile cache."""
        self._profile_cache.clear()
        logger.info("🗑️ Profile cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return len(self._profile_cache)
