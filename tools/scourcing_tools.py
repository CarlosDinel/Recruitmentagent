"""This module contains sourcing tools for various sourcing tasks."""

from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from langchain.tools import tool

# Set up logging with enhanced diagnostics
logger = logging.getLogger(__name__)

# ============================================================================
# DIAGNOSTIC MODE - Set to True for detailed search debugging
# ============================================================================
DIAGNOSTIC_MODE = False

def _diagnostic_log(message: str, data: Any = None, level: str = "info"):
    """Log diagnostic information when DIAGNOSTIC_MODE is enabled."""
    if not DIAGNOSTIC_MODE:
        return
    
    prefix = "🔬 [DIAGNOSTIC]"
    if level == "info":
        logger.info(f"{prefix} {message}")
    elif level == "warning":
        logger.warning(f"{prefix} {message}")
    elif level == "error":
        logger.error(f"{prefix} {message}")
    elif level == "debug":
        logger.debug(f"{prefix} {message}")
    
    if data is not None:
        if isinstance(data, dict):
            logger.info(f"{prefix} Data: {json.dumps(data, indent=2, default=str)[:2000]}")
        else:
            logger.info(f"{prefix} Data: {str(data)[:2000]}")

# ---- Configuration ----
UNIPILE_BASE_URL = "https://api.unipile.com/v1"
# Note: API key should be loaded from environment variables in production

# Try to use new LinkedIn API client if available
try:
    from src.infrastructure.external_services.linkedin.linkedin_api_client import LinkedInAPIClient
    _LINKEDIN_CLIENT_AVAILABLE = True
except ImportError:
    _LINKEDIN_CLIENT_AVAILABLE = False
    logger.warning("New LinkedIn API client not available, using fallback implementation")

# ---- Tools ----

@tool
def search_candidates_integrated_cursor_and_no_cursor(
    project_id: str, 
    search_id: str,
    max_results: int = 50,
    location: str = "",
    keywords: str = "",
    company_name: str = "",
    job_title: str = "",
        skills: str = "",  # Changed from List[str] to str for tool compatibility
        experience_level: str = "",
        use_cursor: bool = True
) -> str:  # Changed return type to str for tool compatibility
    """
    Searches for candidates on LinkedIn using both cursor-based and non-cursor-based methods.
    
    This tool is designed to be used by the Candidate Searching Agent to find LinkedIn profiles
    that match specific hiring criteria for a given project.
    
    Args:
        project_id: Unique identifier for the hiring project
        search_id: Unique identifier for this search within the project
        max_results: Maximum number of candidates to return (default: 50)
        location: Geographic location filter (e.g., "Amsterdam", "Netherlands")
        keywords: Keywords to search for in profiles
        company_name: Current or previous company filter
        job_title: Job title filter
        skills: Comma-separated list of skills to search for
        experience_level: Experience level filter (Junior, Mid, Senior, Executive)
        use_cursor: Whether to use cursor-based pagination for large result sets
        
    Returns:
        JSON string containing search results and metadata
    """
    logger.info(f"🔍 Starting LinkedIn candidate search for project {project_id}, search {search_id}")
    
    # DIAGNOSTIC: Log all input parameters
    _diagnostic_log("=" * 60)
    _diagnostic_log("LINKEDIN TOOL: search_candidates_integrated_cursor_and_no_cursor")
    _diagnostic_log("=" * 60)
    _diagnostic_log(f"Input Parameters:")
    _diagnostic_log(f"  project_id: {project_id}")
    _diagnostic_log(f"  search_id: {search_id}")
    _diagnostic_log(f"  max_results: {max_results}")
    _diagnostic_log(f"  location: '{location}'")
    _diagnostic_log(f"  keywords: '{keywords}'")
    _diagnostic_log(f"  company_name: '{company_name}'")
    _diagnostic_log(f"  job_title: '{job_title}'")
    _diagnostic_log(f"  skills: '{skills}'")
    _diagnostic_log(f"  experience_level: '{experience_level}'")
    _diagnostic_log(f"  use_cursor: {use_cursor}")
    
    # Check if all search params are empty
    if not any([location, keywords, company_name, job_title, skills, experience_level]):
        _diagnostic_log("⚠️ ALL SEARCH PARAMETERS ARE EMPTY!", level="warning")
        _diagnostic_log("This will likely result in no candidates being found!", level="warning")
    
    try:
        # Parse skills from comma-separated string
        skills_list = [skill.strip() for skill in skills.split(",") if skill.strip()] if skills else []
        _diagnostic_log(f"Parsed skills_list: {skills_list}")
        
        # Prepare search criteria
        search_criteria = _prepare_search_criteria(
            location=location,
            keywords=keywords,
            company_name=company_name,
            job_title=job_title,
            skills=skills_list,
            experience_level=experience_level
        )
        
        logger.info(f"📋 Search criteria prepared: {search_criteria}")
        _diagnostic_log("Prepared search_criteria:", search_criteria)
        
        # Execute search strategy
        _diagnostic_log(f">>> Executing search with cursor={use_cursor}...")
        if use_cursor:
            candidates = _search_with_cursor_pagination(search_criteria, max_results)
        else:
            candidates = _search_without_cursor(search_criteria, max_results)
        
        _diagnostic_log(f"Raw API returned {len(candidates)} candidates")
        if candidates:
            _diagnostic_log(f"First raw candidate sample:", candidates[0] if candidates else "None")
        else:
            _diagnostic_log("⚠️ LinkedIn API returned ZERO candidates!", level="warning")
        
        # Process and enrich candidate data
        processed_candidates = []
        skipped_count = 0
        for candidate in candidates:
            processed_candidate = _process_candidate_data(candidate)
            if processed_candidate:
                processed_candidates.append(processed_candidate)
            else:
                skipped_count += 1
        
        _diagnostic_log(f"Processing complete: {len(processed_candidates)} valid, {skipped_count} skipped")
        
        # Prepare response
        response = {
            "success": True,
            "search_metadata": {
                "project_id": project_id,
                "search_id": search_id,
                "total_found": len(processed_candidates),
                "search_criteria": search_criteria,
                "search_timestamp": datetime.now().isoformat()
            },
            "candidates": processed_candidates,
            "pagination": {
                "has_more": len(candidates) == max_results,
                "next_cursor": _generate_next_cursor(candidates) if use_cursor else None,
                "page_size": len(processed_candidates)
            }
        }
        
        logger.info(f"✅ Search completed: {len(processed_candidates)} candidates found")
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"❌ LinkedIn candidate search failed: {e}")
        error_response = {
            "success": False,
            "error": str(e),
            "search_metadata": {
                "project_id": project_id,
                "search_id": search_id,
                "total_found": 0,
                "search_timestamp": datetime.now().isoformat()
            },
            "candidates": [],
            "pagination": {"has_more": False, "next_cursor": None, "page_size": 0}
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)

def _prepare_search_criteria(
    location: str,
    keywords: str,
    company_name: str,
    job_title: str,
    skills: List[str],
    experience_level: str
) -> Dict[str, Any]:
    """
    Prepare search criteria for LinkedIn API.
    
    IMPROVED: Simplified query construction for better LinkedIn results.
    - Prioritizes job title and keywords over skills
    - Avoids cluttering query with too many terms
    - Location is passed as separate filter, not in query string
    """
    
    criteria = {
        "type": "people",
        "filters": {},
        "query_parts": []
    }
    
    # Location filter (keep separate, don't add to query - let API handle it)
    if location:
        criteria["filters"]["location"] = location
        # Note: Location is NOT added to query_parts - it's a separate API filter
    
    # Build a focused query - prioritize job title
    primary_query_parts = []
    
    # Job title is most important for finding relevant candidates
    if job_title:
        criteria["filters"]["job_title"] = job_title
        primary_query_parts.append(job_title)
    
    # Add keywords (but limit to avoid cluttering)
    if keywords:
        criteria["filters"]["keywords"] = keywords
        # Only add first 3-4 significant keywords
        keyword_list = [k.strip() for k in keywords.split() if len(k.strip()) > 2]
        primary_query_parts.extend(keyword_list[:4])
    
    # Company filter
    if company_name:
        criteria["filters"]["current_company"] = company_name
        primary_query_parts.append(company_name)
    
    # Skills - add to filters but limit query impact
    if skills:
        criteria["filters"]["skills"] = skills
        # Only add top 2 skills to query to avoid over-filtering
        for skill in skills[:2]:
            primary_query_parts.append(skill)
    
    # Experience level - add to filters, optional query modifier
    if experience_level:
        criteria["filters"]["experience_level"] = experience_level
        if experience_level.lower() in ["senior", "lead", "principal"]:
            primary_query_parts.append("senior")
        elif experience_level.lower() in ["junior", "entry"]:
            primary_query_parts.append("junior")
    
    # Construct final query - deduplicate and limit
    seen = set()
    unique_parts = []
    for part in primary_query_parts:
        part_lower = part.lower()
        if part_lower not in seen:
            seen.add(part_lower)
            unique_parts.append(part)
    
    # Limit query to avoid being too restrictive
    criteria["query_parts"] = unique_parts[:6]
    criteria["query"] = " ".join(unique_parts[:6]) if unique_parts else ""
    
    return criteria

def _search_with_cursor_pagination(search_criteria: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
    """Execute LinkedIn search using cursor-based pagination."""
    
    logger.info("🔄 Using cursor-based pagination for large result sets")
    
    all_candidates = []
    cursor = None
    page_size = min(25, max_results)  # LinkedIn API typically limits to 25 per page
    
    while len(all_candidates) < max_results:
        try:
            # Prepare API request
            search_params = {
                "query": search_criteria.get("query", ""),
                "limit": page_size,
                "type": "people"
            }
            
            if cursor:
                search_params["cursor"] = cursor
            
            # Add filters
            if search_criteria.get("filters"):
                search_params.update(search_criteria["filters"])
            
            # Real LinkedIn API call using new infrastructure or fallback
            candidates_page = _real_linkedin_api_call(search_params)
            
            if not candidates_page.get("data"):
                break
            
            all_candidates.extend(candidates_page["data"])
            
            # Check for more pages
            if not candidates_page.get("has_more") or not candidates_page.get("next_cursor"):
                break
                
            cursor = candidates_page["next_cursor"]
            
        except Exception as e:
            logger.error(f"❌ Error in cursor pagination: {e}")
            break
    
    return all_candidates[:max_results]

def _search_without_cursor(search_criteria: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
    """Execute LinkedIn search without cursor pagination (single request)."""
    
    logger.info("📄 Using single request without pagination")
    
    try:
        # Prepare API request
        search_params = {
            "query": search_criteria.get("query", ""),
            "limit": min(max_results, 100),  # Single request limit
            "type": "people"
        }
        
        # Add filters
        if search_criteria.get("filters"):
            search_params.update(search_criteria["filters"])
        
        # Real LinkedIn API call using new infrastructure or fallback
        result = _real_linkedin_api_call(search_params)
        
        return result.get("data", [])
        
    except Exception as e:
        logger.error(f"❌ Error in non-cursor search: {e}")
        return []

def _process_candidate_data(candidate_raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process and structure raw candidate data from LinkedIn API."""
    
    try:
        # Determine profile URLs and identifiers
        profile_url = candidate_raw.get("profile_url") or candidate_raw.get("linkedin_url")
        if not profile_url and candidate_raw.get("id"):
            profile_url = f"https://linkedin.com/in/{candidate_raw.get('id')}"
        provider_id = candidate_raw.get("provider_id") or candidate_raw.get("id", "")

        # Extract basic information
        processed = {
            "provider_id": provider_id,
            "naam": _extract_full_name(candidate_raw),
            "positie": candidate_raw.get("current_position", ""),
            "headline": candidate_raw.get("headline", ""),
            "locatie": candidate_raw.get("location", ""),
            "experience": _calculate_experience(candidate_raw),
            "skills": _extract_skills(candidate_raw),
            "LinkedIn_Beschrijving": candidate_raw.get("summary", ""),
            "otw": _assess_open_to_work(candidate_raw),
            "profile_url": profile_url or "",
            "linkedin_url": profile_url or "",
            "current_company": _extract_current_company(candidate_raw),
            "previous_companies": _extract_previous_companies(candidate_raw),
            "education": _extract_education(candidate_raw),
            "years_active": _calculate_years_active(candidate_raw),
            "recent_posts": _extract_recent_posts(candidate_raw)
        }
        
        # Validate required fields
        if not processed["provider_id"] or not processed["naam"] or not processed["linkedin_url"]:
            logger.warning(f"⚠️ Skipping candidate with missing required fields")
            return None
        
        return processed
        
    except Exception as e:
        logger.error(f"❌ Error processing candidate data: {e}")
        return None

def _extract_full_name(candidate: Dict[str, Any]) -> str:
    """Extract full name from candidate data."""
    first_name = candidate.get("first_name", "")
    last_name = candidate.get("last_name", "")
    full_name = candidate.get("full_name", "")
    
    if full_name:
        return full_name
    elif first_name and last_name:
        return f"{first_name} {last_name}"
    else:
        return candidate.get("name", "Unknown")

def _calculate_experience(candidate: Dict[str, Any]) -> str:
    """Calculate total years of experience."""
    experiences = candidate.get("experience", [])
    if not experiences:
        return "Not specified"
    
    total_years = 0
    for exp in experiences:
        years = exp.get("duration_years", 0)
        total_years += years
    
    if total_years == 0:
        return "Not specified"
    elif total_years < 2:
        return f"{total_years} year{'s' if total_years != 1 else ''}"
    else:
        return f"{total_years}+ years"

def _extract_skills(candidate: Dict[str, Any]) -> List[str]:
    """Extract skills from candidate profile."""
    skills = candidate.get("skills", [])
    if isinstance(skills, list):
        return [skill.get("name", skill) if isinstance(skill, dict) else str(skill) for skill in skills]
    return []

def _assess_open_to_work(candidate: Dict[str, Any]) -> str:
    """Assess if candidate is open to work opportunities."""
    # Check for explicit open to work indicators
    if candidate.get("open_to_work", False):
        return "Yes"
    
    # Check for recent job search activity indicators
    if candidate.get("recent_job_search_activity", False):
        return "Yes"
    
    # Check headline for job search keywords
    headline = candidate.get("headline", "").lower()
    job_search_keywords = ["seeking", "looking for", "open to", "available", "job search"]
    
    if any(keyword in headline for keyword in job_search_keywords):
        return "Yes"
    
    # Check recent posts for job search content
    recent_posts = candidate.get("recent_posts", [])
    for post in recent_posts:
        content = post.get("content", "").lower()
        if any(keyword in content for keyword in job_search_keywords):
            return "Yes"
    
    return "Unknown"

def _extract_current_company(candidate: Dict[str, Any]) -> str:
    """Extract current company information."""
    experience = candidate.get("experience", [])
    if experience:
        current = experience[0]  # Assuming first is most recent
        return current.get("company", "")
    return ""

def _extract_previous_companies(candidate: Dict[str, Any]) -> List[str]:
    """Extract previous companies."""
    experience = candidate.get("experience", [])
    companies = []
    for exp in experience[1:]:  # Skip current (first) position
        company = exp.get("company", "")
        if company and company not in companies:
            companies.append(company)
    return companies

def _extract_education(candidate: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract education information."""
    education = candidate.get("education", [])
    processed_education = []
    
    for edu in education:
        processed_education.append({
            "school": edu.get("school", ""),
            "degree": edu.get("degree", ""),
            "field": edu.get("field_of_study", ""),
            "years": edu.get("years", "")
        })
    
    return processed_education

def _calculate_years_active(candidate: Dict[str, Any]) -> int:
    """Calculate years active in industry."""
    experiences = candidate.get("experience", [])
    if not experiences:
        return 0
    
    # Find earliest start date
    start_years = []
    for exp in experiences:
        start_year = exp.get("start_year")
        if start_year:
            start_years.append(int(start_year))
    
    if start_years:
        earliest_year = min(start_years)
        current_year = datetime.now().year
        return max(0, current_year - earliest_year)
    
    return 0

def _extract_recent_posts(candidate: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract recent posts information."""
    posts = candidate.get("recent_posts", [])
    processed_posts = []
    
    for post in posts[:5]:  # Limit to 5 most recent posts
        processed_posts.append({
            "post_id": post.get("id", ""),
            "content": post.get("content", "")[:200] + "..." if len(post.get("content", "")) > 200 else post.get("content", ""),
            "date": post.get("created_date", ""),
            "engagement": post.get("engagement_count", 0)
        })
    
    return processed_posts

def _generate_next_cursor(candidates: List[Dict[str, Any]]) -> Optional[str]:
    """Generate next cursor for pagination."""
    if candidates:
        last_candidate = candidates[-1]
        return f"cursor_{last_candidate.get('id', 'unknown')}_{len(candidates)}"
    return None

def _real_linkedin_api_call(search_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real LinkedIn API call using Unipile API.
    Falls back to mock if API is not available or fails.
    """
    # DIAGNOSTIC: Log API call entry
    _diagnostic_log("-" * 40)
    _diagnostic_log("LINKEDIN API CALL (_real_linkedin_api_call)")
    _diagnostic_log("-" * 40)
    _diagnostic_log("Search params received:", search_params)
    _diagnostic_log(f"LinkedIn client available: {_LINKEDIN_CLIENT_AVAILABLE}")
    
    # Try to use new LinkedIn API client
    if _LINKEDIN_CLIENT_AVAILABLE:
        try:
            from src.infrastructure.external_services.linkedin.linkedin_api_client import LinkedInAPIClient
            _diagnostic_log("✅ LinkedInAPIClient imported successfully")
            
            # Create client instance
            client = LinkedInAPIClient()
            _diagnostic_log("✅ LinkedInAPIClient instantiated")
            
            # Extract search parameters
            query = search_params.get("query", "")
            location = search_params.get("location", "")
            company = search_params.get("current_company", "")
            title = search_params.get("job_title", "")
            skills_param = search_params.get("skills", [])
            
            # Handle both list and string formats for skills
            if isinstance(skills_param, str):
                skills = [s.strip() for s in skills_param.split(",")] if skills_param else None
            elif isinstance(skills_param, list):
                skills = skills_param if skills_param else None
            else:
                skills = None
            
            limit = search_params.get("limit", 25)
            cursor = search_params.get("cursor")
            
            # Build comprehensive query string
            query_parts = []
            if query:
                query_parts.append(query)
            if title:
                query_parts.append(title)
            if skills:
                query_parts.extend(skills[:3])  # Add top 3 skills to query
            
            search_query = " ".join(query_parts) if query_parts else None
            
            logger.info(f"🔍 Real LinkedIn API search: query='{search_query}', location='{location}', limit={limit}")
            _diagnostic_log(f">>> Calling client.search_people()...")
            _diagnostic_log(f"    query: '{search_query}'")
            _diagnostic_log(f"    location: '{location}'")
            _diagnostic_log(f"    company: '{company}'")
            _diagnostic_log(f"    title: '{title}'")
            _diagnostic_log(f"    skills: {skills}")
            _diagnostic_log(f"    limit: {limit}")
            _diagnostic_log(f"    cursor: {cursor}")
            
            # Make synchronous API call using correct Unipile format
            result = client.search_people(
                query=search_query,
                location=location if location else None,
                company=company if company else None,
                title=title if title else None,
                skills=skills,
                limit=limit,
                cursor=cursor,
                api_type="classic"  # Use classic API (most compatible)
            )
            
            _diagnostic_log(f">>> API call completed")
            _diagnostic_log(f"Raw result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            _diagnostic_log(f"Result type: {type(result).__name__}")
            
            # Transform result to expected format
            items = result.get("items", result.get("data", []))
            _diagnostic_log(f"Items extracted: {len(items)} candidates")
            
            # Map LinkedIn API response to expected format
            candidates = []
            for item in items:
                # Extract profile URL from id if needed
                profile_url = item.get("profile_url") or item.get("linkedin_url", "")
                if not profile_url and item.get("id"):
                    profile_url = f"https://linkedin.com/in/{item.get('id')}"
                
                candidate = {
                    "id": item.get("id") or item.get("provider_id", ""),
                    "provider_id": item.get("provider_id") or item.get("id", ""),
                    "first_name": item.get("first_name", ""),
                    "last_name": item.get("last_name", ""),
                    "full_name": item.get("full_name") or item.get("name") or item.get("display_name", "LinkedIn Member"),
                    "headline": item.get("headline", ""),
                    "location": item.get("location", ""),
                    "current_position": item.get("current_position") or item.get("title", ""),
                    "current_company": item.get("current_company") or item.get("company", ""),
                    "summary": item.get("summary", ""),
                    "profile_url": profile_url,
                    "linkedin_url": profile_url,
                    "experience": item.get("experience", []),
                    "skills": item.get("skills", []),
                    "education": item.get("education", []),
                    "open_to_work": item.get("open_to_work", False),
                    "recent_posts": item.get("recent_posts", []),
                    # Include all original data for compatibility
                    **item
                }
                candidates.append(candidate)
            
            logger.info(f"✅ Real LinkedIn API successful: {len(candidates)} candidates found")
            _diagnostic_log(f"✅ LinkedIn API call SUCCESS: {len(candidates)} candidates")
            if candidates:
                _diagnostic_log(f"First candidate from API:", candidates[0])
            
            return {
                "data": candidates,
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor") or result.get("cursor")
            }
            
        except Exception as e:
            logger.error(f"❌ Real LinkedIn API error: {e}")
            _diagnostic_log(f"❌ LinkedIn API EXCEPTION: {str(e)}", level="error")
            import traceback
            _diagnostic_log(f"Traceback: {traceback.format_exc()}", level="error")
            logger.debug(traceback.format_exc())
            # Fall through to mock implementation
    else:
        _diagnostic_log("⚠️ LinkedInAPIClient not available, using fallback", level="warning")
    
    # Fallback to mock if new infrastructure not available or error occurred
    logger.warning("⚠️ Using mock LinkedIn API (fallback - set LINKEDIN_API_KEY to use real API)")
    _diagnostic_log(">>> Falling back to MOCK LinkedIn API")
    return _mock_linkedin_api_call(search_params)

def _mock_linkedin_api_call(search_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock LinkedIn API call for development/testing purposes.
    Replace this with actual Unipile API integration.
    """
    logger.info(f"🧪 Mock API call with params: {search_params}")
    
    # Generate mock candidates based on search criteria
    mock_candidates = []
    num_results = min(search_params.get("limit", 25), 25)
    
    for i in range(num_results):
        candidate = {
            "id": f"linkedin_user_{i+1:03d}",
            "first_name": f"Candidate",
            "last_name": f"Name{i+1}",
            "headline": f"Senior Developer at Tech Company {i+1}",
            "location": search_params.get("location", "Amsterdam, Netherlands"),
            "current_position": f"Senior Software Engineer",
            "summary": f"Experienced developer with expertise in {search_params.get('query', 'technology')}",
            "experience": [
                {
                    "company": f"Tech Company {i+1}",
                    "position": "Senior Software Engineer",
                    "duration_years": 3,
                    "start_year": 2021
                },
                {
                    "company": f"Previous Company {i+1}",
                    "position": "Software Engineer",
                    "duration_years": 2,
                    "start_year": 2019
                }
            ],
            "skills": ["Python", "JavaScript", "React", "Node.js", "SQL"],
            "education": [
                {
                    "school": f"University {i+1}",
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "years": "2015-2019"
                }
            ],
            "open_to_work": i % 3 == 0,  # Every 3rd candidate is open to work
            "recent_posts": [
                {
                    "id": f"post_{i+1}_1",
                    "content": "Excited about new technologies in software development!",
                    "created_date": "2025-11-01",
                    "engagement_count": 15
                }
            ],
            "profile_url": f"https://linkedin.com/in/candidate-name{i+1}"
        }
        mock_candidates.append(candidate)
    
    return {
        "data": mock_candidates,
        "has_more": len(mock_candidates) == search_params.get("limit", 25),
        "next_cursor": f"mock_cursor_{len(mock_candidates)}" if len(mock_candidates) == search_params.get("limit", 25) else None
    }

@tool
def LinkedIn_profile_scrape(profile_url: str) -> str:
    """
    Scrapes a LinkedIn profile given its URL.
    
    This tool extracts detailed profile information from a LinkedIn profile URL.
    Used by the Profile Scraping Agent to get comprehensive candidate data.
    
    Args:
        profile_url: The LinkedIn profile URL to scrape
        
    Returns:
        Dictionary containing detailed profile information:
        {
            "success": bool,
            "profile_data": {
                "provider_id": str,
                "naam": str,
                "headline": str,
                "locatie": str,
                "current_position": str,
                "current_company": str,
                "experience": list,
                "education": list,
                "skills": list,
                "summary": str,
                "contact_info": dict,
                "recent_activities": list,
                "recommendations": list,
                "languages": list,
                "certifications": list
            },
            "scrape_metadata": {
                "scrape_timestamp": str,
                "profile_url": str,
                "data_freshness": str
            }
        }
    """
    logger.info(f"🔍 Scraping LinkedIn profile: {profile_url}")
    
    try:
        # Validate URL
        if not profile_url or "linkedin.com" not in profile_url:
            raise ValueError("Invalid LinkedIn profile URL")
        
        # Extract profile ID from URL
        profile_id = _extract_profile_id_from_url(profile_url)
        
        # Scrape profile data (mock implementation)
        profile_data = _scrape_profile_data(profile_url, profile_id)
        
        response = {
            "success": True,
            "profile_data": profile_data,
            "scrape_metadata": {
                "scrape_timestamp": datetime.now().isoformat(),
                "profile_url": profile_url,
                "data_freshness": "real-time"
            }
        }
        
        logger.info(f"✅ Profile scraped successfully: {profile_data.get('naam', 'Unknown')}")
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Profile scraping failed: {e}")
        error_response = {
            "success": False,
            "error": str(e),
            "scrape_metadata": {
                "scrape_timestamp": datetime.now().isoformat(),
                "profile_url": profile_url,
                "data_freshness": "failed"
            }
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)

@tool
def match_candidates_to_job(candidates_json: str, job_description: str) -> str:
    """
    Matches candidates to a job description based on their profiles.
    
    This tool analyzes candidate profiles against job requirements and provides
    matching scores and recommendations.
    
    Args:
        candidates_json: JSON string containing list of candidate profiles
        job_description: Job description with requirements
        
    Returns:
        JSON string with matching analysis results
    """
    logger.info(f"🎯 Matching candidates to job requirements")
    
    try:
        # Parse candidates from JSON string
        candidates_data = json.loads(candidates_json)
        
        # Handle different input formats
        if isinstance(candidates_data, dict) and 'candidates' in candidates_data:
            candidates = candidates_data['candidates']
        elif isinstance(candidates_data, list):
            candidates = candidates_data
        else:
            raise ValueError("Invalid candidates data format")
        
        if not candidates:
            return json.dumps([], ensure_ascii=False, indent=2)
        
        if not job_description:
            raise ValueError("Job description cannot be empty")
        
        logger.info(f"🎯 Matching {len(candidates)} candidates to job requirements")
        
        # Parse job requirements
        job_requirements = _parse_job_requirements(job_description)
        
        # Match each candidate
        matched_candidates = []
        for candidate in candidates:
            match_analysis = _analyze_candidate_match(candidate, job_requirements)
            
            matched_candidate = {
                "candidate": candidate,
                "match_analysis": match_analysis
            }
            matched_candidates.append(matched_candidate)
        
        # Sort by overall score (descending)
        matched_candidates.sort(key=lambda x: x["match_analysis"]["overall_score"], reverse=True)
        
        logger.info(f"✅ Candidate matching completed. Top score: {matched_candidates[0]['match_analysis']['overall_score']:.1f}%")
        return json.dumps(matched_candidates, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Candidate matching failed: {e}")
        error_response = {"error": str(e), "matched_candidates": []}
        return json.dumps(error_response, ensure_ascii=False, indent=2)

# ---- Helper Functions ----

def _extract_profile_id_from_url(profile_url: str) -> str:
    """Extract LinkedIn profile ID from URL."""
    try:
        # Extract ID from LinkedIn URL patterns
        if "/in/" in profile_url:
            parts = profile_url.split("/in/")
            if len(parts) > 1:
                profile_id = parts[1].split("/")[0].split("?")[0]
                return profile_id
        
        # Fallback: use hash of URL
        import hashlib
        return hashlib.md5(profile_url.encode()).hexdigest()[:16]
        
    except Exception:
        return "unknown_profile"

def _scrape_profile_data(profile_url: str, profile_id: str) -> Dict[str, Any]:
    """
    Scrape detailed profile data from LinkedIn using Unipile API.
    Falls back to mock data if API is not available.
    """
    
    # Try to use real Unipile API
    if _LINKEDIN_CLIENT_AVAILABLE:
        try:
            from src.infrastructure.external_services.linkedin.linkedin_api_client import LinkedInAPIClient
            
            client = LinkedInAPIClient()
            
            logger.info(f"🔍 Real profile scraping for: {profile_id}")
            
            # Call Unipile API to get full profile
            profile_data = client.get_user_profile(
                provider_public_id=profile_id,
                linkedin_sections="*"  # Get all sections
            )
            
            # Transform Unipile response to internal format
            if profile_data and isinstance(profile_data, dict):
                # Extract work experience
                work_history = []
                if profile_data.get("positions"):
                    for position in profile_data.get("positions", []):
                        work_history.append({
                            "company": position.get("company_name", ""),
                            "position": position.get("title", ""),
                            "duration": position.get("date_range", ""),
                            "duration_years": position.get("duration_years", 0),
                            "description": position.get("description", ""),
                            "start_year": position.get("start_year"),
                            "end_year": position.get("end_year")
                        })
                
                # Extract education
                education_list = []
                if profile_data.get("education"):
                    for edu in profile_data.get("education", []):
                        education_list.append({
                            "school": edu.get("school_name", ""),
                            "degree": edu.get("degree", ""),
                            "field_of_study": edu.get("field_of_study", ""),
                            "years": edu.get("date_range", ""),
                            "start_year": edu.get("start_year"),
                            "end_year": edu.get("end_year")
                        })
                
                # Extract skills
                skills_list = []
                if profile_data.get("skills"):
                    skills_list = [skill.get("name", skill) if isinstance(skill, dict) else skill 
                                  for skill in profile_data.get("skills", [])]
                
                # Extract certifications
                certifications_list = []
                if profile_data.get("certifications"):
                    for cert in profile_data.get("certifications", []):
                        certifications_list.append({
                            "name": cert.get("name", ""),
                            "issuing_organization": cert.get("authority", ""),
                            "issue_date": cert.get("date", ""),
                            "credential_url": cert.get("url", "")
                        })
                
                # Build complete profile
                enriched_profile = {
                    "provider_id": profile_data.get("id") or profile_id,
                    "naam": profile_data.get("display_name") or profile_data.get("full_name", "Unknown"),
                    "headline": profile_data.get("headline", ""),
                    "locatie": profile_data.get("location", {}).get("name", "") if isinstance(profile_data.get("location"), dict) else profile_data.get("location", ""),
                    "current_position": work_history[0].get("position", "") if work_history else "",
                    "current_company": work_history[0].get("company", "") if work_history else "",
                    "experience": work_history,
                    "education": education_list,
                    "skills": skills_list,
                    "summary": profile_data.get("summary", ""),
                    "contact_info": {
                        "email": profile_data.get("email", ""),
                        "phone": profile_data.get("phone", ""),
                        "twitter": profile_data.get("twitter", ""),
                        "website": profile_data.get("websites", [])
                    },
                    "recent_activities": profile_data.get("posts", []),
                    "recommendations": profile_data.get("recommendations", []),
                    "languages": profile_data.get("languages", []),
                    "certifications": certifications_list,
                    "connections_count": profile_data.get("connections_count", 0),
                    "followers_count": profile_data.get("followers_count", 0),
                    "profile_picture": profile_data.get("picture_url", "")
                }
                
                logger.info(f"✅ Real profile scraping successful: {enriched_profile.get('naam')}")
                return enriched_profile
            
        except Exception as e:
            logger.error(f"❌ Real profile scraping error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Fall through to mock
    
    # Fallback to mock profile data
    logger.warning(f"⚠️ Using mock profile data for {profile_id} (set LINKEDIN_API_KEY to use real API)")
    
    mock_profile = {
        "provider_id": f"linkedin_{profile_id}",
        "naam": "John Doe",
        "headline": "Senior Software Engineer | Full-Stack Developer | Tech Lead",
        "locatie": "Amsterdam, Netherlands",
        "current_position": "Senior Software Engineer",
        "current_company": "Tech Innovations B.V.",
        "experience": [
            {
                "company": "Tech Innovations B.V.",
                "position": "Senior Software Engineer",
                "duration": "2022 - Present",
                "duration_years": 2,
                "description": "Leading development of scalable web applications using React and Node.js"
            },
            {
                "company": "Digital Solutions Ltd.",
                "position": "Software Engineer",
                "duration": "2020 - 2022",
                "duration_years": 2,
                "description": "Developed full-stack applications using Python and JavaScript"
            }
        ],
        "education": [
            {
                "school": "University of Amsterdam",
                "degree": "Master of Science",
                "field_of_study": "Computer Science",
                "years": "2018 - 2020"
            }
        ],
        "skills": [
            "JavaScript", "Python", "React", "Node.js", "SQL", "MongoDB", 
            "AWS", "Docker", "Git", "Agile Development"
        ],
        "summary": "Passionate software engineer with 5+ years of experience in full-stack development. Expertise in modern web technologies and cloud platforms.",
        "contact_info": {
            "email": "john.doe@example.com",
            "phone": "+31 6 12345678"
        },
        "recent_activities": [
            {
                "type": "post",
                "content": "Excited to share our latest project using React and GraphQL!",
                "date": "2025-10-30",
                "engagement": 25
            }
        ],
        "recommendations": [
            {
                "recommender": "Jane Smith",
                "position": "Team Lead at Tech Innovations B.V.",
                "content": "John is an exceptional developer with strong problem-solving skills."
            }
        ],
        "languages": ["English (Fluent)", "Dutch (Intermediate)", "Spanish (Basic)"],
        "certifications": [
            {
                "name": "AWS Certified Developer",
                "issuer": "Amazon Web Services",
                "date": "2024"
            }
        ]
    }
    
    return mock_profile

def _parse_job_requirements(job_description: str) -> Dict[str, Any]:
    """Parse job description to extract requirements using LLM for intelligent analysis."""
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        system_prompt = """You are an expert job requirements analyst. Extract structured requirements from job descriptions.
        
Output valid JSON with this exact structure:
{
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...],
  "experience_years": 0,
  "education_level": "",
  "location": "",
  "job_title": "",
  "industry": ""
}

Extract ALL skills mentioned (technical, soft skills, domain knowledge, tools, etc.).
Be comprehensive and accurate. If information is not mentioned, use empty string or 0."""
        
        human_prompt = f"""Extract requirements from this job description:

{job_description}

Return ONLY valid JSON, no additional text."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Clean markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        requirements = json.loads(response_text)
        logger.info(f"📝 Extracted requirements via LLM: {len(requirements.get('required_skills', []))} required skills, {requirements.get('experience_years', 0)} years experience")
        
        return requirements
        
    except Exception as e:
        logger.warning(f"⚠️ LLM parsing failed, using fallback: {e}")
        
        # Fallback to basic parsing
        requirements = {
            "required_skills": [],
            "preferred_skills": [],
            "experience_years": 0,
            "education_level": "",
            "location": "",
            "job_title": "",
            "industry": ""
        }
        
        description_lower = job_description.lower()
        
        # Extract common skills (broader list)
        common_skills = [
            "python", "javascript", "java", "react", "node.js", "sql", "mongodb",
            "aws", "docker", "kubernetes", "git", "agile", "scrum", "html", "css",
            "accounting", "excel", "powerpoint", "word", "finance", "bookkeeping",
            "leadership", "management", "communication", "teamwork", "problem solving"
        ]
        
        for skill in common_skills:
            if skill in description_lower:
                requirements["required_skills"].append(skill.title())
        
        # Extract experience requirements
        import re
        exp_patterns = [
            r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
            r"(\d+)\+?\s*years?\s*in",
            r"minimum\s*(\d+)\s*years?"
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, description_lower)
            if match:
                requirements["experience_years"] = int(match.group(1))
                break
        
        # Extract location if mentioned
        locations = ["amsterdam", "rotterdam", "utrecht", "den haag", "netherlands"]
        for location in locations:
            if location in description_lower:
                requirements["location"] = location.title()
                break
        
        logger.info(f"📝 Fallback extraction: {len(requirements['required_skills'])} skills")
        return requirements

def _analyze_candidate_match(candidate: Dict[str, Any], job_requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze how well a candidate matches job requirements using LLM for intelligent evaluation."""
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Prepare candidate summary
        candidate_skills = candidate.get("skills", [])
        candidate_title = candidate.get("title", candidate.get("headline", ""))
        candidate_company = candidate.get("company", "")
        candidate_location = candidate.get("location", candidate.get("locatie", ""))
        candidate_experience = candidate.get("experience", [])
        
        system_prompt = """You are an expert recruiter evaluating candidate fit. Analyze the candidate against job requirements and provide detailed scoring.

Output valid JSON with this EXACT structure:
{
  "overall_score": 0.0,
  "skills_match": {
    "score": 0.0,
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill3", "skill4"]
  },
  "experience_match": {
    "score": 0.0,
    "relevant_experience": "X years in relevant roles",
    "experience_gap": "Description of any gaps"
  },
  "location_match": {
    "score": 0.0,
    "distance": "Local/Remote/Relocation required"
  },
  "education_match": {
    "score": 0.0,
    "relevant_education": ["degree info"]
  },
  "recommendation": "Brief recommendation",
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1", "concern2"]
}

Scoring guide (0-100):
- 90-100: Exceptional match
- 80-89: Strong match
- 70-79: Good match
- 60-69: Acceptable match
- 50-59: Marginal match
- Below 50: Poor match

Be honest and evidence-based. Consider skill transferability and potential."""
        
        human_prompt = f"""Evaluate this candidate:

CANDIDATE:
- Name: {candidate.get('name', candidate.get('naam', 'Unknown'))}
- Current Role: {candidate_title}
- Company: {candidate_company}
- Location: {candidate_location}
- Skills: {', '.join(candidate_skills) if candidate_skills else 'Not specified'}
- Experience: {len(candidate_experience)} positions listed

JOB REQUIREMENTS:
- Required Skills: {', '.join(job_requirements.get('required_skills', [])) if job_requirements.get('required_skills') else 'Not specified'}
- Preferred Skills: {', '.join(job_requirements.get('preferred_skills', [])) if job_requirements.get('preferred_skills') else 'Not specified'}
- Experience Required: {job_requirements.get('experience_years', 0)} years
- Location: {job_requirements.get('location', 'Not specified')}
- Job Title: {job_requirements.get('job_title', 'Not specified')}

Provide detailed evaluation. Return ONLY valid JSON."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Clean markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        match_analysis = json.loads(response_text)
        logger.info(f"🤖 LLM evaluation: {match_analysis.get('overall_score', 0):.1f}% overall, {len(match_analysis.get('skills_match', {}).get('matched_skills', []))} skills matched")
        
        return match_analysis
        
    except Exception as e:
        logger.warning(f"⚠️ LLM evaluation failed, using fallback: {e}")
        
        # Fallback to algorithmic matching
        candidate_skills = [skill.lower() for skill in candidate.get("skills", [])]
        required_skills = [skill.lower() for skill in job_requirements.get("required_skills", [])]
        
        if required_skills:
            matched_skills = [skill for skill in required_skills if skill in candidate_skills]
            skills_score = (len(matched_skills) / len(required_skills)) * 100
            missing_skills = [skill for skill in required_skills if skill not in candidate_skills]
        else:
            matched_skills = []
            skills_score = 50
            missing_skills = []
        
        # Experience matching
        candidate_experience = _calculate_total_experience(candidate)
        required_experience = job_requirements.get("experience_years", 0)
        
        if required_experience > 0:
            if candidate_experience >= required_experience:
                experience_score = 100
            elif candidate_experience >= required_experience * 0.8:
                experience_score = 80
            elif candidate_experience >= required_experience * 0.6:
                experience_score = 60
            else:
                experience_score = 40
        else:
            experience_score = 70
        
        # Location matching
        candidate_location = candidate.get("locatie", candidate.get("location", "")).lower()
        required_location = job_requirements.get("location", "").lower()
        
        if required_location and candidate_location:
            if required_location in candidate_location or candidate_location in required_location:
                location_score = 100
            elif "netherlands" in candidate_location and "netherlands" in required_location:
                location_score = 80
            else:
                location_score = 30
        else:
            location_score = 70
        
        # Education matching
        education_score = 75
        candidate_education = candidate.get("education", [])
        if candidate_education:
            for edu in candidate_education:
                degree = edu.get("degree", "").lower()
                field = edu.get("field_of_study", "").lower()
                if any(term in degree or term in field for term in ["computer", "software", "engineering", "technology", "accounting", "finance", "business"]):
                    education_score = 90
                    break
        
        # Overall score (weighted average)
        overall_score = (
            skills_score * 0.4 +
            experience_score * 0.3 +
            location_score * 0.2 +
            education_score * 0.1
        )
        
        # Generate recommendation
        if overall_score >= 80:
            recommendation = "Strong candidate - highly recommended for interview"
        elif overall_score >= 65:
            recommendation = "Good candidate - recommend for phone screening"
        elif overall_score >= 50:
            recommendation = "Potential candidate - consider with reservations"
        else:
            recommendation = "Weak match - not recommended unless other factors compensate"
        
        # Identify strengths and concerns
        strengths = []
        concerns = []
        
        if skills_score >= 80:
            strengths.append("Excellent technical skills match")
        elif skills_score < 50:
            concerns.append("Limited technical skills alignment")
        
        if experience_score >= 80:
            strengths.append("Strong relevant experience")
        elif experience_score < 50:
            concerns.append("Insufficient experience level")
        
        if location_score >= 80:
            strengths.append("Good location match")
        elif location_score < 50:
            concerns.append("Location mismatch may require relocation")
        
        logger.info(f"📊 Fallback evaluation: {overall_score:.1f}% overall")
        
        return {
            "overall_score": round(overall_score, 1),
            "skills_match": {
                "score": round(skills_score, 1),
                "matched_skills": [skill.title() for skill in matched_skills],
                "missing_skills": [skill.title() for skill in missing_skills]
            },
            "experience_match": {
                "score": round(experience_score, 1),
                "relevant_experience": f"{candidate_experience} years",
                "experience_gap": f"Requires {required_experience} years minimum" if candidate_experience < required_experience else "Meets requirement"
            },
            "location_match": {
                "score": round(location_score, 1),
                "distance": "Local" if location_score >= 80 else "Remote/Relocation required"
            },
            "education_match": {
                "score": round(education_score, 1),
                "relevant_education": [edu.get("degree", "") + " in " + edu.get("field_of_study", "") for edu in candidate.get("education", [])]
            },
            "recommendation": recommendation,
            "strengths": strengths,
            "concerns": concerns
        }

def _calculate_total_experience(candidate: Dict[str, Any]) -> int:
    """Calculate total years of experience for a candidate."""
    experiences = candidate.get("experience", [])
    if not experiences:
        return 0
    
    total_years = 0
    for exp in experiences:
        if isinstance(exp, dict):
            years = exp.get("duration_years", 0)
            if isinstance(years, (int, float)):
                total_years += years
    
    return int(total_years)
