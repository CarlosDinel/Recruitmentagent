"""This module contains various database agent tools and utilities for interacting with databases.
It includes functions for querying, inserting, updating, and deleting records in the database.
It also includes tools for vectorizing data and performing similarity searches using vector databases.
The tools are designed to be modular and can be easily integrated into larger systems for recruitment and talent
acquisition.
"""


# ---- Package imports ----
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from dotenv import load_dotenv
import os
import pymongo
from datetime import datetime
import logging
from pymongo.errors import PyMongoError
load_dotenv()


# ---- Tools list ----
tools_list = [
    "create_project",
    "validate_project_structure",
    "quick_save_candidate",
    "get_projects",
    "update_project",
    "delete_project",
    "search_candidates_by_skills",
    "save_candidate",
    "get_candidate_by_id",
    "update_candidate",
    "delete_candidate",
    
]
#  ---- Your code here ----
class DatabaseTools:
    """Class encapsulating database agent tools."""

    def __init__(self):
        # Try MONGO_URI first, then build from individual components
        uri = os.getenv('MONGO_URI')
        
        if not uri:
            # Build URI from individual components
            username = os.getenv('MONGO_USERNAME')
            password = os.getenv('MONGO_PASSWORD')
            host = os.getenv('MONGO_HOST')
            database = os.getenv('MONGO_DATABASE') or os.getenv('MONGO_DB') or 'test_db'
            
            if username and password and host:
                # MongoDB Atlas connection string
                uri = f"mongodb+srv://{username}:{password}@{host}/{database}?retryWrites=true&w=majority"
            else:
                # Fallback to localhost if no config
                uri = f"mongodb://localhost:27017/{database}"
                self.logger = logging.getLogger(__name__)
                self.logger.warning("MongoDB config incomplete, using localhost fallback")
        
        if not uri:
            raise ValueError("MongoDB URI not configured. Set MONGO_URI or MONGO_USERNAME/PASSWORD/HOST")
        
        self.client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
        # Fix: Use MONGO_DATABASE instead of MONGO_DB
        db_name = os.getenv('MONGO_DATABASE') or os.getenv('MONGO_DB') or 'test_db'
        self.db = self.client[db_name]
        self.logger = logging.getLogger(__name__)

        
    @tool
    def create_project(project_data: Dict[str, Any]) -> int:
        """Create a new project in the database."""
        try:

            username = os.getenv('MONGO_USERNAME')
            password = os.getenv('MONGO_PASSWORD')
            host = os.getenv('MONGO_HOST')
            database = os.getenv('MONGO_DATABASE')

            uri = f"mongodb+srv://{username}:{password}@{host}/{database}?retryWrites=true&w=majority"
            client = pymongo.MongoClient(uri)
            db = client[database]

            # Validate and structure project data according to your format
            structured_project = validate_and_structure_project(project_data)

            existing_project = db.projects.find_one({"_id": structured_project["_id"]})

            if existing_project:
                result = db.projects.replace_one(
                    {"_id": structured_project["_id"]}, 
                    structured_project
                )
                action = "updated"
                project_id = structured_project["_id"]
            else:
                result = db.projects.insert_one(structured_project)
                action = "created"
                project_id = str(result.inserted_id)

            client.close()
            return {
                "success": True,
                "project_id": project_id,
                "action": action,
                "message": f"Project {action} successfully"
            }
        except PyMongoError as e:
            self.logger.error(f"Database error while creating project: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create project"
            }

    def validate_and_structure_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and structure project data according to the specified format.
        
        Required fields:
        - title: Project title (required)
        - project_id: Unique project identifier (required)
        - company: Company name (required)
        - status: Project status (required, defaults to 'active')
        
        Optional fields:
        - name: Alternative name
        - description: Project description
        - requirements: Detailed requirements
        - skills_needed: Array of required skills
        - location: Job location
        - job_type: Type of employment
        - salary_range: Salary information
        - urgency: Urgency level
        - department: Company department
        - linkedin_search_parameters: Search parameters for LinkedIn
        - created_at: Creation timestamp
        - updated_at: Update timestamp
        """
        from datetime import datetime
        
        # Check required fields
        required_fields = ['title', 'project_id', 'company']
        for field in required_fields:
            if not project_data.get(field):
                raise ValueError(f"Required field '{field}' is missing or empty")
        
        # Create structured project with required and optional fields
        structured_project = {
            # Required fields
            "title": project_data["title"],
            "project_id": project_data["project_id"], 
            "company": project_data["company"],
            "status": project_data.get("status", "active"),  # Default to active
            
            # Optional fields - only include if provided
            "name": project_data.get("name", ""),
            "description": project_data.get("description", ""),
            "requirements": project_data.get("requirements", ""),
            "location": project_data.get("location", ""),
            "job_type": project_data.get("job_type", ""),
            "salary_range": project_data.get("salary_range", ""),
            "department": project_data.get("department", ""),
            "urgency": project_data.get("urgency", "normal"),
            
            # Skills array - validate it's a list
            "skills_needed": project_data.get("skills_needed", []) if isinstance(project_data.get("skills_needed"), list) else [],
            
            # LinkedIn search parameters - validate it's a dict
            "linkedin_search_parameters": project_data.get("linkedin_search_parameters", {}) if isinstance(project_data.get("linkedin_search_parameters"), dict) else {},
            
            # Timestamps
            "created_at": project_data.get("created_at", datetime.now().isoformat()),
            "updated_at": project_data.get("updated_at", datetime.now().isoformat())
        }
        
        # Clean up empty optional fields if desired (uncomment to remove empty strings)
        # structured_project = {k: v for k, v in structured_project.items() 
        #                      if v or k in required_fields + ['status', 'urgency', 'skills_needed', 'linkedin_search_parameters']}
        
        return structured_project

    @tool
    def update_project(project_id: int, update_data: Dict[str, Any], update_timestamp: str) -> bool:
        """Update an existing project in the database."""
        client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
        db = client[os.getenv("MONGODB_DB")]
        result = db.projects.update_one(
            {"_id": project_id},
            {"$set": {**update_data, "updated_at": update_timestamp}}
        )
        return result.modified_count > 0

    @tool
    def get_projects(query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve projects from the database based on a query."""
        # Direct database access to avoid recursion
        import os
        username = os.getenv('MONGO_USERNAME')
        password = os.getenv('MONGO_PASSWORD')
        host = os.getenv('MONGO_HOST')
        db_name = os.getenv('MONGO_DATABASE') or 'test_db'
        
        if not all([username, password, host, db_name]):
            return []
        
        uri = f"mongodb+srv://{username}:{password}@{host}/{db_name}?retryWrites=true&w=majority"
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
        db = client[db_name]
        
        try:
            if query is None:
                query = {}
            projects = list(db.projects.find(query))
            # Convert ObjectId to string for JSON serialization
            for project in projects:
                if "_id" in project:
                    project["_id"] = str(project["_id"])
            return projects
        except Exception as e:
            print(f"Error retrieving projects: {e}")
            return []
        finally:
            client.close()
    
    @tool
    def save_candidate(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save candidate information to the database with validation and structure.
        
        Args:
            candidate_data: Dictionary containing candidate information in the specified format
            
        Returns:
            Dictionary with success status, candidate_id, and message
        """
        try:
            # Get database connection using config from .env
            username = os.getenv('MONGO_USERNAME')
            password = os.getenv('MONGO_PASSWORD')
            host = os.getenv('MONGO_HOST')
            database = os.getenv('MONGO_DATABASE')
            
            uri = f"mongodb+srv://{username}:{password}@{host}/{database}?retryWrites=true&w=majority"
            client = pymongo.MongoClient(uri)
            db = client[database]
            
            # Validate and structure candidate data according to your format
            structured_candidate = validate_and_structure_candidate(candidate_data)
            
            # Check if candidate already exists (by _id which is full name)
            existing_candidate = db.candidates.find_one({"_id": structured_candidate["_id"]})

            
            if existing_candidate:
                # Update existing candidate
                result = db.candidates.replace_one(
                    {"_id": structured_candidate["_id"]}, 
                    structured_candidate
                )
                action = "updated"
                candidate_id = structured_candidate["_id"]
            else:
                # Insert new candidate
                result = db.candidates.insert_one(structured_candidate)
                action = "created"
                candidate_id = str(result.inserted_id)
            
            client.close()
            
            return {
                "success": True,
                "candidate_id": candidate_id,
                "action": action,
                "message": f"Candidate {action} successfully"
            }
    
            
        except PyMongoError as e:   
            self.logger.error(f"Database error while saving candidate: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save candidate"
            }

@tool
def validate_project_structure(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test project validation without saving to database.
    
    Args:
        project_data: Dictionary containing project information
        
    Returns:
        Dictionary with validation results and structured project
    """
    try:
        # Create a temporary DatabaseTools instance for validation
        db_tools = DatabaseTools()
        structured_project = db_tools.validate_and_structure_project(project_data)
        
        return {
            "success": True,
            "valid": True,
            "structured_project": structured_project,
            "message": "Project structure is valid",
            "required_fields_present": ["title", "project_id", "company", "status"],
            "optional_fields_used": [k for k, v in structured_project.items() 
                                   if k not in ["title", "project_id", "company", "status"] and v]
        }
        
    except ValueError as e:
        return {
            "success": False,
            "valid": False,
            "error": str(e),
            "message": "Project validation failed - missing required fields"
        }
    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "error": str(e),
            "message": "Unexpected validation error"
        }


def validate_and_structure_candidate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and structure candidate data according to the specified format.
    Uses LinkedIn URL as unique identifier (_id) to prevent duplicates and enable profile updates.
    """
    from datetime import datetime
    
    # Use LinkedIn URL as unique identifier, fallback to name if URL not available
    linkedin_url = data.get("linkedin_url", "").strip()
    unique_id = linkedin_url if linkedin_url else data.get("_id", data.get("name", "Unknown"))
    
    # Create structured candidate with all required fields
    structured = {
        "_id": unique_id,  # LinkedIn URL as unique identifier
        "name": data.get("name", data.get("full_name", "Unknown")),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "linkedin_url": linkedin_url,  # Store LinkedIn URL for reference
        "positie": data.get("title", data.get("current_position", data.get("positie", data.get("position", "")))),
        "locatie": data.get("location", data.get("locatie", "")),
        "provider_id": data.get("provider_id", data.get("linkedin_id", "")),
        "headline": data.get("headline", data.get("summary", "")),
        
        # Experience array - validate structure
        "experience": validate_experience_array(data.get("experience", [])),
        "experience_years": data.get("experience_years", 0),
        
        # Skills array
        "skills": data.get("skills", []) if isinstance(data.get("skills", []), list) else [],
        
        "LinkedIn_Beschrijving": data.get("linkedin_description", data.get("LinkedIn_Beschrijving", data.get("description", ""))),
        
        # Posts array - validate structure
        "posts": validate_posts_array(data.get("posts", [])),
        
        # Project linking
        "projectid": data.get("project_id", data.get("projectid", "")),
        "naam_project": data.get("project_name", data.get("naam_project", "")),
        "open_to_work": data.get("open_to_work", "Unknown"),
        
        # Sourcing Manager specific fields
        "pipeline_stage": data.get("pipeline_stage", "sourced"),
        "sourced_at": data.get("sourced_at", datetime.utcnow().isoformat() + "Z"),
        "suitability_status": data.get("suitability_status", "unknown"),
        "suitability_score": data.get("suitability_score", 0),
        "suitability_reasoning": data.get("suitability_reasoning", ""),
        "source": data.get("source", "SourcingManager"),
        "profile_version": data.get("profile_version", "basic"),
        "last_updated": data.get("last_updated", datetime.utcnow().isoformat() + "Z"),
        "evaluation_metadata": data.get("evaluation_metadata", {}),
        
        # Enrichment fields
        "profile_enriched": data.get("profile_enriched", False),
        "enriched_at": data.get("enriched_at", ""),
        "enrichment_details": data.get("enrichment_details", {}),
        "enrichment_timestamp": data.get("enrichment_timestamp", ""),
        
        # Contact moments with default structure
        "contactmomenten": validate_contact_moments(data.get("contactmomenten", {})),
        
        "connectieVerzoekWerknemer": data.get("connectieVerzoekWerknemer", False),
        "isConnectie": data.get("isConnectie", False),
        "Status": data.get("status", data.get("Status", "Uncontacted")),
        
        # Campaign array - validate structure
        "campaign": validate_campaign_array(data.get("campaign", [])),
        
        # Add metadata
        "created_at": data.get("created_at", datetime.utcnow().isoformat() + "Z"),
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    return structured

def validate_experience_array(experience_data: Any) -> List[Dict[str, Any]]:
    """Validate and structure experience array according to the specified data model.
    
    Expected format:
    [
        {
            "company_id": "unique_company_identifier", 
            "company": "Company Name",
            "position": "Job Title",
            "location": "Job Location", 
            "description": "Job description and achievements",
            "skills": ["skill1", "skill2", "skill3"],
            "start": "MM/DD/YYYY",
            "end": "MM/DD/YYYY or null/empty for ongoing"
        }
    ]
    """
    if not isinstance(experience_data, list):
        return []
    
    validated_experience = []
    for exp in experience_data:
        if isinstance(exp, dict):
            # Validate and normalize each experience entry
            validated_exp = {
                "company_id": str(exp.get("company_id", exp.get("companyId", ""))),
                "company": str(exp.get("company", exp.get("companyName", ""))),
                "position": str(exp.get("position", exp.get("title", exp.get("jobTitle", "")))),
                "location": str(exp.get("location", exp.get("jobLocation", ""))),
                "description": str(exp.get("description", exp.get("jobDescription", ""))),
                "skills": validate_skills_list(exp.get("skills", [])),
                "start": normalize_date_format(exp.get("start", exp.get("startDate", ""))),
                "end": normalize_date_format(exp.get("end", exp.get("endDate", "")))
            }
            
            # Only add if we have at least company and position
            if validated_exp["company"] or validated_exp["position"]:
                validated_experience.append(validated_exp)
    
    return validated_experience

def validate_skills_list(skills_data: Any) -> List[str]:
    """Validate skills list to ensure it's a proper list of strings."""
    if not skills_data:
        return []
    
    if isinstance(skills_data, str):
        # If it's a comma-separated string, split it
        return [skill.strip() for skill in skills_data.split(",") if skill.strip()]
    
    if isinstance(skills_data, list):
        # Convert all items to strings and filter empty ones
        return [str(skill).strip() for skill in skills_data if str(skill).strip()]
    
    return []

def normalize_date_format(date_input: Any) -> str:
    """Normalize date to MM/DD/YYYY format or return empty string."""
    if not date_input or str(date_input).lower() in ['null', 'none', 'present', 'current']:
        return ""
    
    date_str = str(date_input).strip()
    
    # If already in correct format MM/DD/YYYY, return as is
    if len(date_str.split('/')) == 3:
        return date_str
    
    # Try to parse other common formats and convert
    try:
        from datetime import datetime as dt
        
        # Try various date formats
        formats_to_try = [
            '%Y-%m-%d',      # 2023-01-15
            '%d-%m-%Y',      # 15-01-2023  
            '%m-%d-%Y',      # 01-15-2023
            '%Y/%m/%d',      # 2023/01/15
            '%d/%m/%Y',      # 15/01/2023
            '%B %Y',         # January 2023
            '%b %Y',         # Jan 2023
            '%Y'             # 2023 (year only)
        ]
        
        for fmt in formats_to_try:
            try:
                parsed_date = dt.strptime(date_str, fmt)
                return parsed_date.strftime('%m/%d/%Y')
            except ValueError:
                continue
                
    except ImportError:
        pass
    
    # If all parsing fails, return original string
    return date_str

# Helper function to create experience entries
def create_experience_entry(
    company: str,
    position: str,
    start_date: str = "",
    end_date: str = "",
    location: str = "",
    description: str = "",
    skills: List[str] = None,
    company_id: str = ""
) -> Dict[str, Any]:
    """Helper function to create a properly formatted experience entry.
    
    Args:
        company: Company name (required)
        position: Job title/position (required) 
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format (empty for ongoing)
        location: Job location
        description: Job description and achievements
        skills: List of skills used in this role
        company_id: Unique company identifier
        
    Returns:
        Dictionary formatted according to the data model
    """
    return {
        "company_id": company_id or "",
        "company": company,
        "position": position,
        "location": location,
        "description": description,
        "skills": skills or [],
        "start": normalize_date_format(start_date),
        "end": normalize_date_format(end_date)
    }

def validate_posts_array(posts_data: Any) -> List[Dict[str, str]]:
    """Validate and structure posts array."""
    if not isinstance(posts_data, list):
        return []
    
    validated_posts = []
    for post in posts_data:
        if isinstance(post, dict):
            validated_post = {
                "post_id": str(post.get("post_id", "")),
                "text": str(post.get("text", ""))
            }
            validated_posts.append(validated_post)
    
    return validated_posts

def validate_contact_moments(contact_data: Any) -> Dict[str, Any]:
    """Validate and structure contact moments."""
    if not isinstance(contact_data, dict):
        contact_data = {}
    
    return {
        "connectie_verzoek": contact_data.get("connectie_verzoek", False),
        "isConnectie": contact_data.get("isConnectie", False),
        "post_geliked": contact_data.get("post_geliked", False),
        "linkedin_bericht": contact_data.get("linkedin_bericht", False),
        "inmail": contact_data.get("inmail", False),
        "email": contact_data.get("email", False),
        "email_datum": contact_data.get("email_datum", "")
    }

def validate_campaign_array(campaign_data: Any) -> List[Dict[str, Any]]:
    """Validate and structure campaign array."""
    if not isinstance(campaign_data, list):
        return []
    
    validated_campaigns = []
    for campaign in campaign_data:
        if isinstance(campaign, dict):
            validated_campaign = {
                "outreachCampaign_num": campaign.get("outreachCampaign_num", campaign.get("campaign_num", "")),
                "active": campaign.get("active", False),
                "startDate": campaign.get("startDate", None),
                "endDate": campaign.get("endDate", None)
            }
            validated_campaigns.append(validated_campaign)
    
            return validated_campaigns

    @tool 
    def get_candidates(query: Optional[Dict[str, Any]] = None, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve candidates from the database with optional filtering.
        
        Args:
            query: Optional MongoDB query for filtering candidates
            project_id: Optional project ID to filter candidates by project
            
        Returns:
            List of candidate dictionaries matching the query
        """
        try:
            # Get database connection
            username = os.getenv('MONGO_USERNAME')
            password = os.getenv('MONGO_PASSWORD') 
            host = os.getenv('MONGO_HOST')
            database = os.getenv('MONGO_DATABASE')
            
            uri = f"mongodb+srv://{username}:{password}@{host}/{database}?retryWrites=true&w=majority"
            client = pymongo.MongoClient(uri)
            db = client[database]
            
            # Build query
            if query is None:
                query = {}
            
            # Add project filter if specified
            if project_id:
                query["projectid"] = project_id
            
            # Execute query
            candidates = list(db.candidates.find(query))
            
            # Convert ObjectId to string for JSON serialization
            for candidate in candidates:
                if "_id" in candidate and not isinstance(candidate["_id"], str):
                    candidate["_id"] = str(candidate["_id"])
            
            client.close()
            
            return candidates
            
        except Exception as e:
            print(f"Error retrieving candidates: {e}")
            return []

    @tool
    def update_candidate_status(candidate_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update candidate with flexible data structure.
        
        Args:
            candidate_id: The candidate's _id (LinkedIn URL or fallback identifier)
            update_data: Dictionary of fields to update (can include status, enrichment data, etc.)
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get database connection
            username = os.getenv('MONGO_USERNAME')
            password = os.getenv('MONGO_PASSWORD')
            host = os.getenv('MONGO_HOST') 
            database = os.getenv('MONGO_DATABASE') or os.getenv('MONGO_DB') or 'test_db'
            
            uri = f"mongodb+srv://{username}:{password}@{host}/{database}?retryWrites=true&w=majority"
            client = pymongo.MongoClient(uri)
            db = client[database]
            
            # Add updated timestamp to all updates
            update_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            
            # Update candidate using LinkedIn URL as identifier
            result = db.candidates.update_one(
                {"_id": candidate_id},
                {"$set": update_data}
            )
            
            client.close()
            
            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": f"Candidate {candidate_id} updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Candidate {candidate_id} not found or no changes made"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update candidate"
            }

    @tool
    def search_candidates_by_skills(skills: List[str], project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search candidates by skills with optional project filtering.
        
        Args:
            skills: List of skills to search for
            project_id: Optional project ID to limit search scope
            
        Returns:
            List of candidates matching the skills criteria
        """
        try:
            # Build query for skills matching
            query = {
                "skills": {"$in": skills}  # Candidates that have any of the specified skills
            }
            
            # Add project filter if specified
            if project_id:
                query["projectid"] = project_id
            
            return DatabaseTools.get_candidates(query)
            
        except Exception as e:
            print(f"Error searching candidates by skills: {e}")
            return []


# ---- Quick Save Functions ----

@tool
def quick_save_candidate(
    name: str,
    LinkedIn_url: str = "",
    email: str = "",
    position: str = "",
    company: str = "",
    skills: str = "",
    location: str = "",
    project_id: str = ""
) -> Dict[str, Any]:
    """Quick save candidate with basic info and current job as experience.
    
    Args:
        name: Full name
        LinkedIn_url: LinkedIn profile URL
        email: Email address
        position: Current position
        company: Current company
        skills: Comma-separated skills string
        location: Current location
        project_id: Associated project ID
    """
    try:
        # Parse skills from string
        skills_list = [skill.strip() for skill in skills.split(",") if skill.strip()] if skills else []
        
        # Create experience entry if company/position provided
        experience_data = []
        if company and position:
            experience_data = [
                create_experience_entry(
                    company=company,
                    position=position,
                    location=location,
                    skills=skills_list,
                    start_date="",  # Current job
                    end_date=""
                )
            ]
        
        candidate_data = {
            "full_name": name,
            "linkedin_url": LinkedIn_url,
            "email": email,
            "current_position": position,
            "location": location,
            "experience": experience_data,
            "skills": skills_list,
            "project_id": project_id
        }
        
        db_tools = DatabaseTools()
        return db_tools.save_candidate(candidate_data)
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to quick save candidate"
        }