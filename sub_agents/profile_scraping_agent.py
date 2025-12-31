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
import os
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
            
            # Update prospects in database via DatabaseAgent
            if enriched_candidates:
                updated_count = self._update_prospects_in_database(enriched_candidates)
                response["enrichment_stats"]["database_updated"] = updated_count
                logger.info(f"💾 Updated {updated_count} prospects in database via DatabaseAgent")
            
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
        """Merge scraped profile data with existing candidate data, including company history."""
        
        enriched = candidate.copy()
        
        # Add enrichment source
        enriched["enrichment_source"] = "cache" if from_cache else "live_scrape"
        
        # Merge work experience
        if "work_experience" in profile_data:
            enriched["work_experience"] = profile_data["work_experience"]
        
        # ENHANCED: Extract and enrich company history with background information
        if "work_experience" in profile_data:
            company_history = self._extract_company_history(profile_data["work_experience"])
            enriched["company_history"] = company_history
            logger.info(f"✅ Extracted company history for {len(company_history)} companies")
        
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
        
        # DEEP ANALYSIS: Add advanced profile insights
        if "work_experience" in enriched and enriched["work_experience"]:
            # Career progression analysis
            enriched["career_analysis"] = self.analyze_career_progression(enriched["work_experience"])
            
            # Achievement extraction
            enriched["achievements"] = self.extract_achievements_and_impact(enriched["work_experience"])
            
            # Skill evolution analysis
            enriched["skill_analysis"] = self.analyze_skill_evolution(
                enriched["work_experience"],
                enriched.get("skills", [])
            )
            
            # Comprehensive profile summary
            enriched["deep_profile_summary"] = self.generate_deep_profile_summary(enriched)
            
            logger.info(f"✅ Deep profile analysis completed for {enriched.get('name', 'candidate')}")
        
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
    
    def _update_prospects_in_database(self, enriched_candidates: List[Dict[str, Any]]) -> int:
        """
        Update enriched prospects in database via DatabaseAgent.
        
        Updates existing prospect documents with enriched profile data including
        work experience, education, skills, certifications, etc.
        
        Args:
            enriched_candidates: List of enriched candidate dictionaries
            
        Returns:
            Number of prospects successfully updated
        """
        logger.info(f"📤 Updating {len(enriched_candidates)} prospects in database...")
        
        try:
            from agents.database_agent import DatabaseAgent, DatabaseAgentState
            
            # Initialize DatabaseAgent
            db_state = DatabaseAgentState(
                name="ProfileEnrichment_DatabaseAgent",
                description="Database operations for profile enrichment",
                tools=[], tool_descriptions=[], tool_input_types=[], tool_output_types=[],
                input_type="dict", output_type="dict", intermediate_steps=[],
                max_iterations=5, iteration_count=0, stop=False,
                last_action="", last_observation="", last_input="", last_output="",
                graph=None, memory=[], memory_limit=100, verbose=False,
                temperature=0.7, top_k=50, top_p=0.9, frequency_penalty=0.0, presence_penalty=0.0,
                best_of=1, n=1, logit_bias={}, seed=42, model=os.getenv("OPENAI_MODEL", "gpt-5"), api_key=""
            )
            
            db_agent = DatabaseAgent(db_state)
            
            # Update each enriched candidate
            updated_count = 0
            for candidate in enriched_candidates:
                try:
                    linkedin_url = candidate.get("linkedin_url") or candidate.get("profile_url")
                    
                    if not linkedin_url:
                        logger.warning(f"⚠️ Skipping candidate without LinkedIn URL: {candidate.get('full_name')}")
                        continue
                    
                    # Prepare updates for prospect
                    updates = {
                        "enrichment_status": candidate.get("enrichment_status", "success"),
                        "enrichment_timestamp": candidate.get("enrichment_timestamp"),
                        "enrichment_source": candidate.get("enrichment_source", "live_scrape")
                    }
                    
                    # Add enriched fields if available
                    if "work_experience" in candidate:
                        updates["work_experience"] = candidate["work_experience"]
                    
                    if "education" in candidate:
                        updates["education"] = candidate["education"]
                    
                    if "skills" in candidate:
                        updates["skills"] = candidate["skills"]
                    
                    if "certifications" in candidate:
                        updates["certifications"] = candidate["certifications"]
                    
                    if "languages" in candidate:
                        updates["languages"] = candidate["languages"]
                    
                    if "endorsements" in candidate:
                        updates["endorsements"] = candidate["endorsements"]
                    
                    if "profile_summary" in candidate:
                        updates["profile_summary"] = candidate["profile_summary"]
                    
                    if "headline" in candidate:
                        updates["headline"] = candidate["headline"]
                    
                    if "connections_count" in candidate:
                        updates["connections_count"] = candidate["connections_count"]
                    
                    # Update prospect via DatabaseAgent
                    success = db_agent.update_prospect(linkedin_url, updates)
                    
                    if success:
                        updated_count += 1
                        logger.debug(f"✅ Updated prospect: {linkedin_url}")
                    else:
                        logger.warning(f"⚠️ Prospect not found for update: {linkedin_url}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update prospect {candidate.get('full_name', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Successfully updated {updated_count}/{len(enriched_candidates)} prospects in database")
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Error updating prospects in database: {e}")
            return 0
    
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
    
    def _extract_company_history(
        self,
        work_experience: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract company background and history from work experience.
        
        Enriches work history with company context:
        - Company name, industry, size
        - Time period at company
        - Career progression
        
        Args:
            work_experience: List of work experience entries
            
        Returns:
            List of enriched company history entries with context
        """
        
        company_history = []
        
        for position in work_experience:
            company_name = position.get("company", "Unknown")
            
            # Create company entry
            company_entry = {
                "company_name": company_name,
                "position_title": position.get("title", "Unknown Position"),
                "employment_type": position.get("employment_type", "Full-time"),
                "start_date": position.get("start_date"),
                "end_date": position.get("end_date"),
                "is_current": position.get("current", False),
                "duration_months": self._calculate_duration(
                    position.get("start_date"),
                    position.get("end_date"),
                    position.get("current", False)
                ),
                "description": position.get("description", "")
            }
            
            # Extract company context clues from position description
            company_context = self._extract_company_context_from_description(
                position.get("description", ""),
                company_name
            )
            
            # Merge context into company entry
            company_entry.update(company_context)
            
            company_history.append(company_entry)
        
        return company_history
    
    def _extract_company_context_from_description(
        self,
        description: str,
        company_name: str
    ) -> Dict[str, Any]:
        """
        Extract company background clues from job description.
        
        Looks for indicators of:
        - Company size (startup, scale-up, enterprise)
        - Industry/domain
        - Company stage (seed, series, growth, mature)
        - Type (B2B, B2C, SaaS, etc.)
        """
        
        context = {
            "industry": None,
            "company_size": None,
            "company_stage": None,
            "company_type": None,
            "inferred_from_description": False
        }
        
        if not description:
            return context
        
        desc_lower = description.lower()
        
        # Size indicators
        if any(term in desc_lower for term in ["startup", "early-stage", "early stage"]):
            context["company_size"] = "Startup"
            context["company_stage"] = "Early"
        elif any(term in desc_lower for term in ["scale-up", "scaling", "hyper-growth", "growth stage"]):
            context["company_size"] = "Growth"
            context["company_stage"] = "Growth"
        elif any(term in desc_lower for term in ["enterprise", "large", "multinational", "global"]):
            context["company_size"] = "Large"
            context["company_stage"] = "Mature"
        elif any(term in desc_lower for term in ["mid-size", "mid size", "medium"]):
            context["company_size"] = "Medium"
            context["company_stage"] = "Established"
        
        # Industry indicators
        if any(term in desc_lower for term in ["fintech", "banking", "finance", "financial services", "investment"]):
            context["industry"] = "Financial Services"
        elif any(term in desc_lower for term in ["healthcare", "pharmaceutical", "biotech", "medical"]):
            context["industry"] = "Healthcare/Biotech"
        elif any(term in desc_lower for term in ["software", "technology", "tech", "saas", "cloud", "development"]):
            context["industry"] = "Technology"
        elif any(term in desc_lower for term in ["consulting", "advisory"]):
            context["industry"] = "Consulting"
        elif any(term in desc_lower for term in ["retail", "e-commerce", "ecommerce", "commerce"]):
            context["industry"] = "Retail/E-commerce"
        elif any(term in desc_lower for term in ["education", "university", "school"]):
            context["industry"] = "Education"
        elif any(term in desc_lower for term in ["manufacturing", "industrial", "production"]):
            context["industry"] = "Manufacturing"
        elif any(term in desc_lower for term in ["marketing", "agency", "advertising"]):
            context["industry"] = "Marketing/Advertising"
        elif any(term in desc_lower for term in ["marketing", "agency", "advertising"]):
            context["industry"] = "Marketing/Advertising"
        
        # Company type indicators
        if any(term in desc_lower for term in ["b2b", "b2c", "b2g"]):
            if "b2b" in desc_lower:
                context["company_type"] = "B2B"
            elif "b2c" in desc_lower:
                context["company_type"] = "B2C"
            elif "b2g" in desc_lower:
                context["company_type"] = "B2G"
        
        # Mark if we extracted useful context
        context["inferred_from_description"] = bool(
            context["industry"] or context["company_size"] or context["company_stage"]
        )
        
        return context
    
    def _calculate_duration(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        is_current: bool
    ) -> int:
        """Calculate employment duration in months."""
        
        if not start_date:
            return 0
        
        try:
            from datetime import datetime
            
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if isinstance(start_date, str) else start_date
            
            if is_current:
                end = datetime.now()
            elif end_date:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if isinstance(end_date, str) else end_date
            else:
                return 0
            
            # Calculate months between dates
            months = (end.year - start.year) * 12 + (end.month - start.month)
            return max(0, months)
        
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate duration: {e}")
            return 0
    
    def analyze_career_progression(self, work_experience: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deep analysis of career progression patterns beyond just skills.
        
        Identifies:
        - Growth trajectory (moving up, lateral, down)
        - Industry consistency vs. diversity
        - Company tier progression (startup → scale-up → enterprise)
        - Skill evolution over time
        - Stability indicators
        """
        
        if not work_experience or len(work_experience) == 0:
            return {}
        
        analysis = {
            "total_positions": len(work_experience),
            "career_span_years": 0,
            "growth_trajectory": "UNKNOWN",
            "industry_focus": "DIVERSE",
            "company_tier_progression": [],
            "position_seniority_trend": "STABLE",
            "job_stability": "MODERATE",
            "career_insights": []
        }
        
        try:
            # Calculate career span
            first_position = work_experience[0]
            last_position = work_experience[-1]
            
            start_date = first_position.get("start_date")
            end_date = last_position.get("end_date") if not last_position.get("current") else None
            
            if start_date:
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if isinstance(start_date, str) else start_date
                    end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date and isinstance(end_date, str) else (datetime.now() if not end_date else end_date)
                    years = (end.year - start.year) + (end.month - start.month) / 12.0
                    analysis["career_span_years"] = round(years, 1)
                except:
                    pass
            
            # Analyze company tier progression
            company_types = []
            for position in work_experience:
                company_name = position.get("company", "")
                desc = position.get("description", "").lower()
                
                # Heuristic detection of company stage
                if any(word in desc for word in ["startup", "early stage", "seed", "series a"]):
                    company_types.append("STARTUP")
                elif any(word in desc for word in ["scale-up", "growth", "series b", "series c"]):
                    company_types.append("SCALE_UP")
                elif any(word in desc for word in ["enterprise", "fortune", "nasdaq", "s&p", "multinational"]):
                    company_types.append("ENTERPRISE")
                else:
                    company_types.append("UNKNOWN")
            
            analysis["company_tier_progression"] = company_types
            
            # Detect progression pattern
            if len(work_experience) >= 2:
                title_progression = []
                for pos in work_experience:
                    title_lower = pos.get("title", "").lower()
                    if any(word in title_lower for word in ["senior", "lead", "principal", "director", "vp", "head", "chief"]):
                        title_progression.append("SENIOR")
                    elif any(word in title_lower for word in ["manager", "manager"]):
                        title_progression.append("MANAGER")
                    elif any(word in title_lower for word in ["junior", "associate"]):
                        title_progression.append("JUNIOR")
                    else:
                        title_progression.append("MID")
                
                # Detect trajectory
                if title_progression[-1] in ["SENIOR", "MANAGER", "DIRECTOR"] and title_progression[0] != "SENIOR":
                    analysis["growth_trajectory"] = "UPWARD"
                    analysis["career_insights"].append("Strong growth trajectory - progressing to senior roles")
                elif all(t == title_progression[0] for t in title_progression):
                    analysis["growth_trajectory"] = "STABLE"
                    analysis["career_insights"].append("Consistent career level - deep expertise in similar roles")
                else:
                    analysis["growth_trajectory"] = "LATERAL"
                    analysis["career_insights"].append("Lateral moves - building diverse expertise")
            
            # Industry consistency analysis
            industries = set()
            for position in work_experience:
                desc = position.get("description", "").lower()
                # Simple industry detection
                if any(word in desc for word in ["tech", "software", "ai", "machine learning", "cloud", "devops"]):
                    industries.add("TECHNOLOGY")
                elif any(word in desc for word in ["finance", "banking", "investment", "trading", "fintech"]):
                    industries.add("FINANCE")
                elif any(word in desc for word in ["healthcare", "medical", "pharma", "biotech"]):
                    industries.add("HEALTHCARE")
                elif any(word in desc for word in ["e-commerce", "retail", "sales", "marketing"]):
                    industries.add("COMMERCE")
            
            if len(industries) == 1:
                analysis["industry_focus"] = "SPECIALIZED"
                analysis["career_insights"].append("Deep specialization in single industry - domain expert")
            elif len(industries) > 1:
                analysis["industry_focus"] = "DIVERSE"
                analysis["career_insights"].append("Cross-industry experience - adaptable generalist")
            
            # Job stability (tenure duration)
            avg_tenure = 0
            tenures = []
            for position in work_experience:
                tenure = position.get("duration_months", 0)
                if tenure > 0:
                    tenures.append(tenure)
            
            if tenures:
                avg_tenure = sum(tenures) / len(tenures)
                if avg_tenure > 36:  # 3+ years average
                    analysis["job_stability"] = "HIGH"
                    analysis["career_insights"].append("Long tenure at positions - committed, deep impact potential")
                elif avg_tenure > 18:  # 1.5+ years
                    analysis["job_stability"] = "MODERATE"
                elif avg_tenure < 12:
                    analysis["job_stability"] = "LOW"
                    analysis["career_insights"].append("Frequent job changes - may indicate high ambition or instability")
            
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing career progression: {e}")
        
        return analysis
    
    def extract_achievements_and_impact(self, work_experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract achievements and measurable impact from job descriptions.
        
        Looks for:
        - Quantifiable results (grew X%, built teams of N, handled $X budget)
        - Leadership achievements (mentored, led, managed)
        - Technical achievements (built, launched, designed)
        - Business impact (revenue, cost savings, efficiency)
        """
        
        achievements = []
        
        try:
            for position in work_experience:
                position_achievements = {
                    "position": position.get("title", "Unknown"),
                    "company": position.get("company", "Unknown"),
                    "quantified_achievements": [],
                    "leadership_achievements": [],
                    "technical_achievements": [],
                    "business_impact": []
                }
                
                desc = position.get("description", "")
                if not desc:
                    continue
                
                # Look for quantified achievements
                import re
                numbers = re.findall(r'(\d+[%]|\$\d+[MK]?|\d+\s*(projects?|teams?|people|users|customers))', desc, re.IGNORECASE)
                if numbers:
                    position_achievements["quantified_achievements"] = list(set(numbers))  # Remove duplicates
                
                # Look for leadership keywords
                leadership_words = ["led", "managed", "mentored", "supervised", "directed", "oversaw", "pioneered", "spearheaded"]
                if any(word in desc.lower() for word in leadership_words):
                    position_achievements["leadership_achievements"].append("Leadership/Management experience demonstrated")
                
                # Look for technical keywords
                technical_words = ["built", "designed", "architected", "implemented", "developed", "engineered", "optimized", "automated"]
                if any(word in desc.lower() for word in technical_words):
                    position_achievements["technical_achievements"].append("Technical delivery/innovation demonstrated")
                
                # Look for business impact keywords
                impact_words = ["revenue", "growth", "cost savings", "efficiency", "market", "launch", "scale", "expand"]
                if any(word in desc.lower() for word in impact_words):
                    position_achievements["business_impact"].append("Business impact/commercial focus demonstrated")
                
                if any(position_achievements[key] for key in position_achievements if key != "position"):
                    achievements.append(position_achievements)
        
        except Exception as e:
            logger.warning(f"⚠️ Error extracting achievements: {e}")
        
        return achievements
    
    def analyze_skill_evolution(self, work_experience: List[Dict[str, Any]], skills: List[str]) -> Dict[str, Any]:
        """
        Analyze how skills have evolved over the candidate's career.
        
        Identifies:
        - Core consistent skills (present throughout career)
        - Emerging skills (learned recently)
        - Breadth vs depth of skills
        - Skill modernization (are they learning new tech?)
        """
        
        analysis = {
            "core_skills": [],
            "emerging_skills": [],
            "total_skills": len(skills),
            "skill_breadth": "MODERATE",
            "technical_depth": "UNKNOWN",
            "continuous_learning": False,
            "modernization_index": 0.5
        }
        
        try:
            # Analyze skill mentions across positions
            skill_frequency = {}
            
            for position in work_experience:
                desc = position.get("description", "").lower()
                for skill in skills:
                    if skill.lower() in desc:
                        skill_frequency[skill] = skill_frequency.get(skill, 0) + 1
            
            # Core skills appear in multiple positions
            if work_experience:
                threshold = len(work_experience) * 0.6
                analysis["core_skills"] = [s for s, freq in skill_frequency.items() if freq >= threshold]
            
            # Emerging skills in recent positions (last 1-2 positions)
            if len(work_experience) >= 1:
                recent_desc = ""
                for position in work_experience[:2]:  # Last 2 positions
                    recent_desc += " " + position.get("description", "").lower()
                
                analysis["emerging_skills"] = [s for s in skills if s.lower() in recent_desc and s not in analysis["core_skills"]]
            
            # Analyze skill breadth
            if len(skills) > 20:
                analysis["skill_breadth"] = "WIDE"
            elif len(skills) > 10:
                analysis["skill_breadth"] = "BROAD"
            elif len(skills) > 5:
                analysis["skill_breadth"] = "MODERATE"
            else:
                analysis["skill_breadth"] = "NARROW"
            
            # Check for modern tech presence (simple heuristic)
            modern_tech = ["python", "javascript", "react", "aws", "kubernetes", "docker", "ai", "machine learning", 
                          "llm", "gpt", "cloud", "devops", "ci/cd", "terraform", "golang"]
            modern_skills = [s for s in skills if any(tech in s.lower() for tech in modern_tech)]
            analysis["modernization_index"] = min(1.0, len(modern_skills) / max(1, len(skills)))
            
            if analysis["modernization_index"] > 0.5:
                analysis["continuous_learning"] = True
            
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing skill evolution: {e}")
        
        return analysis
    
    def generate_deep_profile_summary(self, enriched_candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive deep profile analysis combining all insights.
        
        Returns a summary highlighting:
        - Career narrative (how their career story reads)
        - Unique strengths beyond skills
        - Growth potential
        - Cultural/team fit indicators
        """
        
        summary = {
            "career_narrative": "",
            "unique_strengths": [],
            "growth_potential": "UNKNOWN",
            "learning_agility": "UNKNOWN",
            "leadership_readiness": "UNKNOWN",
            "red_flags": [],
            "profile_score": 0
        }
        
        try:
            work_exp = enriched_candidate.get("work_experience", [])
            skills = enriched_candidate.get("skills", [])
            
            # Run all analyses
            career_prog = self.analyze_career_progression(work_exp)
            achievements = self.extract_achievements_and_impact(work_exp)
            skill_evolution = self.analyze_skill_evolution(work_exp, skills)
            
            # Build career narrative
            trajectory = career_prog.get("growth_trajectory", "UNKNOWN")
            industry = career_prog.get("industry_focus", "DIVERSE")
            span = career_prog.get("career_span_years", 0)
            
            if trajectory == "UPWARD":
                summary["career_narrative"] = f"Strong upward trajectory with {span} years across {industry.lower()} industry. Shows progression to senior roles and continuous growth."
                summary["growth_potential"] = "HIGH"
            elif trajectory == "LATERAL":
                summary["career_narrative"] = f"Strategic lateral moves building broad expertise across {industry.lower()} domains over {span} years. Well-rounded generalist."
                summary["growth_potential"] = "MEDIUM"
            else:
                summary["career_narrative"] = f"Consistent performance with {span} years of experience in {industry.lower()} industry. Deep expertise developer."
                summary["growth_potential"] = "MEDIUM"
            
            # Unique strengths
            insights = career_prog.get("career_insights", [])
            summary["unique_strengths"] = insights
            
            # Learning agility
            if skill_evolution.get("continuous_learning"):
                summary["learning_agility"] = "HIGH"
                summary["unique_strengths"].append("Continuously learning and staying current with technology")
            
            # Leadership readiness
            leadership_count = sum(1 for ach in achievements if ach.get("leadership_achievements"))
            if leadership_count >= 2:
                summary["leadership_readiness"] = "READY"
                summary["unique_strengths"].append("Demonstrated leadership and mentoring experience")
            elif leadership_count >= 1:
                summary["leadership_readiness"] = "DEVELOPING"
            
            # Calculate profile strength score (0-100)
            score = 50  # baseline
            
            if trajectory == "UPWARD":
                score += 15
            if industry == "SPECIALIZED":
                score += 10
            if skill_evolution.get("continuous_learning"):
                score += 10
            if career_prog.get("job_stability") == "HIGH":
                score += 10
            if summary["learning_agility"] == "HIGH":
                score += 5
            if achievements:
                score += 10
            
            summary["profile_score"] = min(100, score)
            
            # Red flags
            if career_prog.get("job_stability") == "LOW":
                summary["red_flags"].append("Frequent job changes - verify commitment/stability")
            if not skill_evolution.get("continuous_learning") and span > 5:
                summary["red_flags"].append("Limited recent skill updates - may lack current tech knowledge")
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating deep profile summary: {e}")
        
        return summary
    
    def clear_cache(self):
        """Clear the profile cache."""
        self._profile_cache.clear()
        logger.info("🗑️ Profile cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return len(self._profile_cache)
