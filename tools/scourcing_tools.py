"""This module contains sourcing tools for various sourcing tasks."""

from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from langchain.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

# ---- Configuration ----
UNIPILE_BASE_URL = "https://api.unipile.com/v1"
# Note: API key should be loaded from environment variables in production

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
    
    try:
        # Parse skills from comma-separated string
        skills_list = [skill.strip() for skill in skills.split(",") if skill.strip()] if skills else []
        
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
        
        # Execute search strategy
        if use_cursor:
            candidates = _search_with_cursor_pagination(search_criteria, max_results)
        else:
            candidates = _search_without_cursor(search_criteria, max_results)
        
        # Process and enrich candidate data
        processed_candidates = []
        for candidate in candidates:
            processed_candidate = _process_candidate_data(candidate)
            if processed_candidate:
                processed_candidates.append(processed_candidate)
        
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
    """Prepare search criteria for LinkedIn API."""
    
    criteria = {
        "type": "people",
        "filters": {},
        "query_parts": []
    }
    
    # Location filter
    if location:
        criteria["filters"]["location"] = location
        criteria["query_parts"].append(f"location:{location}")
    
    # Keywords filter
    if keywords:
        criteria["filters"]["keywords"] = keywords
        criteria["query_parts"].append(keywords)
    
    # Company filter
    if company_name:
        criteria["filters"]["current_company"] = company_name
        criteria["query_parts"].append(f"company:{company_name}")
    
    # Job title filter
    if job_title:
        criteria["filters"]["job_title"] = job_title
        criteria["query_parts"].append(f"title:{job_title}")
    
    # Skills filter
    if skills:
        criteria["filters"]["skills"] = skills
        for skill in skills:
            criteria["query_parts"].append(f"skill:{skill}")
    
    # Experience level filter
    if experience_level:
        criteria["filters"]["experience_level"] = experience_level
        if experience_level.lower() in ["senior", "lead", "principal"]:
            criteria["query_parts"].append("senior OR lead OR principal")
        elif experience_level.lower() in ["junior", "entry"]:
            criteria["query_parts"].append("junior OR entry OR graduate")
    
    # Construct final query
    criteria["query"] = " ".join(criteria["query_parts"]) if criteria["query_parts"] else ""
    
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
            
            # Mock API call (replace with actual Unipile API call)
            candidates_page = _mock_linkedin_api_call(search_params)
            
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
        
        # Mock API call (replace with actual Unipile API call)
        result = _mock_linkedin_api_call(search_params)
        
        return result.get("data", [])
        
    except Exception as e:
        logger.error(f"❌ Error in non-cursor search: {e}")
        return []

def _process_candidate_data(candidate_raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process and structure raw candidate data from LinkedIn API."""
    
    try:
        # Extract basic information
        processed = {
            "provider_id": candidate_raw.get("id", ""),
            "naam": _extract_full_name(candidate_raw),
            "positie": candidate_raw.get("current_position", ""),
            "headline": candidate_raw.get("headline", ""),
            "locatie": candidate_raw.get("location", ""),
            "experience": _calculate_experience(candidate_raw),
            "skills": _extract_skills(candidate_raw),
            "LinkedIn_Beschrijving": candidate_raw.get("summary", ""),
            "otw": _assess_open_to_work(candidate_raw),
            "profile_url": candidate_raw.get("profile_url", ""),
            "current_company": _extract_current_company(candidate_raw),
            "previous_companies": _extract_previous_companies(candidate_raw),
            "education": _extract_education(candidate_raw),
            "years_active": _calculate_years_active(candidate_raw),
            "recent_posts": _extract_recent_posts(candidate_raw)
        }
        
        # Validate required fields
        if not processed["provider_id"] or not processed["naam"]:
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
    Scrape detailed profile data from LinkedIn.
    This is a mock implementation - replace with actual scraping logic.
    """
    
    # Mock profile data
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
    """Parse job description to extract requirements."""
    
    # Simple keyword-based parsing (replace with more sophisticated NLP)
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
    
    # Extract common tech skills
    tech_skills = [
        "python", "javascript", "java", "react", "node.js", "sql", "mongodb",
        "aws", "docker", "kubernetes", "git", "agile", "scrum", "html", "css"
    ]
    
    for skill in tech_skills:
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
    
    return requirements

def _analyze_candidate_match(candidate: Dict[str, Any], job_requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze how well a candidate matches job requirements."""
    
    # Skills matching
    candidate_skills = [skill.lower() for skill in candidate.get("skills", [])]
    required_skills = [skill.lower() for skill in job_requirements.get("required_skills", [])]
    
    if required_skills:
        matched_skills = [skill for skill in required_skills if skill in candidate_skills]
        skills_score = (len(matched_skills) / len(required_skills)) * 100
        missing_skills = [skill for skill in required_skills if skill not in candidate_skills]
    else:
        matched_skills = []
        skills_score = 50  # Neutral score when no requirements specified
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
        experience_score = 70  # Neutral score
    
    # Location matching
    candidate_location = candidate.get("locatie", "").lower()
    required_location = job_requirements.get("location", "").lower()
    
    if required_location and candidate_location:
        if required_location in candidate_location or candidate_location in required_location:
            location_score = 100
        elif "netherlands" in candidate_location and "netherlands" in required_location:
            location_score = 80
        else:
            location_score = 30
    else:
        location_score = 70  # Neutral score
    
    # Education matching (basic)
    education_score = 75  # Default neutral score
    candidate_education = candidate.get("education", [])
    if candidate_education:
        # Check for relevant degrees
        for edu in candidate_education:
            degree = edu.get("degree", "").lower()
            field = edu.get("field_of_study", "").lower()
            if any(term in degree or term in field for term in ["computer", "software", "engineering", "technology"]):
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
