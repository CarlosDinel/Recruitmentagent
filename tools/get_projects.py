""""This moduule contains the tools necessary to get the projects from linkedin API, convert them to JSON format so the database tool can store them properly.
It has tools to get the projects from LinkedIn API, from MongoDB, convert them to JSON format, and a main tool to get all projects with fallback logic.
"""



# ---- Package imports ----
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from dotenv import load_dotenv
import os
import requests
import json
from pymongo import MongoClient
from datetime import datetime

load_dotenv()


#  ---- Configuration ----
def get_linkedin_config():
    """Get LinkedIn API configuration from environment variables."""
    config = {
        'api_key': os.getenv('LINKEDIN_API_KEY'),
        'account_id': os.getenv('LINKEDIN_ACCOUNT_ID'),
        'base_url': os.getenv('LINKEDIN_BASE_URL', 'https://api4.unipile.com:13447/api/v1'),
        'timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
        'max_retries': int(os.getenv('MAX_RETRIES', '3'))
    }
    
    # Validate required fields
    missing_fields = []
    if not config['api_key']:
        missing_fields.append('LINKEDIN_API_KEY')
    if not config['account_id']:
        missing_fields.append('LINKEDIN_ACCOUNT_ID')
        
    if missing_fields:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    return config

def get_mongo_config():
    """Get MongoDB configuration from environment variables."""
    config = {
        'username': os.getenv('MONGO_USERNAME'),
        'password': os.getenv('MONGO_PASSWORD'),
        'host': os.getenv('MONGO_HOST'),
        'database': os.getenv('MONGO_DATABASE'),
        'collection': os.getenv('MONGO_COLLECTION', 'projects')
    }
    
    # Validate required fields
    missing_fields = []
    required_fields = ['username', 'password', 'host', 'database']
    for field in required_fields:
        if not config[field]:
            missing_fields.append(f'MONGO_{field.upper()}')
    
    if missing_fields:
        raise ValueError(f"Missing required MongoDB environment variables: {', '.join(missing_fields)}")
    
    return config

#  ---- Your code here ----

@tool
def get_linkedin_saved_searches() -> List[Dict[str, Any]]:
    """Get saved searches from LinkedIn API using Unipile.
    This retrieves the saved search parameters that can be used for recruitment.
    
    Returns:
        List[Dict[str, Any]]: A list of LinkedIn saved searches with their parameters.
    """
    try:
        config = get_linkedin_config()  # Use environment variables instead of hardcoded values
        
        url = f"{config['base_url']}/linkedin/search/parameters"
        
        headers = {
            "accept": "application/json",
            "X-API-KEY": config['api_key']  # Use from environment
        }
        
        params = {
            "type": "SAVED_SEARCHES",
            "account_id": config['account_id']  # Use from environment
        }
        
        print("🔍 Fetching saved searches from LinkedIn API...")
        
        # Make request with retry logic
        for attempt in range(config['max_retries']):
            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=config['timeout']
                )
                response.raise_for_status()
                break
                
            except requests.exceptions.RequestException as e:
                if attempt == config['max_retries'] - 1:
                    raise e
                print(f"Request failed (attempt {attempt + 1}/{config['max_retries']}): {e}")
        
        data = response.json()
        print(f"LinkedIn API response received")
        
        # Parse the response
        saved_searches = []
        items = data.get('items', [])
        
        for item in items:
            search_data = {
                'id': item.get('id'),
                'title': item.get('title', 'Untitled Search'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
                'object': item.get('object'),
                'additional_data': item.get('additional_data', {}),
                'source': 'linkedin_saved_search'
            }
            saved_searches.append(search_data)
        
        print(f"Retrieved {len(saved_searches)} saved searches")
        return saved_searches
        
    except ValueError as e:
        print(f" Configuration error: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f" Network error fetching LinkedIn saved searches: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f" Error parsing LinkedIn API response: {e}")
        return []
    except Exception as e:
        print(f" Unexpected error fetching saved searches: {e}")
        return []


@tool
def get_projects_from_linkedin_api() -> List[Dict[str, Any]]:
    """Get projects from LinkedIn API using environment configuration.
    
    This function now uses the new LinkedIn API client infrastructure while
    maintaining backward compatibility with the old interface.
    
    Returns:
        List[Dict[str, Any]]: A list of projects from LinkedIn API.
    """
    try:
        # Try to use new infrastructure if available
        try:
            from src.infrastructure.external_services.linkedin.linkedin_api_client import LinkedInAPIClient
            api_client = LinkedInAPIClient()
            items = api_client.get_search_parameters()
            
            projects = []
            for item in items:
                if item.get('object') == 'LinkedinSearchParameter':
                    additional_data = item.get('additional_data', {})
                    project_id = additional_data.get('project_id', '')
                    
                    if project_id:  # Only process items with valid project_id
                        project = {
                            'project_id': project_id,
                            'name': item.get('title', 'Unnamed Project'),
                            'title': item.get('title', ''),
                            'created_at': item.get('created_at', datetime.utcnow().isoformat() + "Z"),
                            'linkedin_search_id': item.get('id', ''),
                            'status': 'active',
                            'source': 'linkedin_api',
                            'details': item  # Full item data for reference
                        }
                        projects.append(project)
            
            print(f"✅ Successfully retrieved {len(projects)} projects from LinkedIn API (using new infrastructure)")
            return projects
            
        except ImportError:
            # Fallback to old implementation if new infrastructure not available
            pass
        
        # Original implementation (fallback)
        config = get_linkedin_config()
        
        url = f"{config['base_url']}/linkedin/search/parameters"
        
        headers = {
            "accept": "application/json",
            "X-API-KEY": config['api_key']
        }
        
        params = {
            "type": "SAVED_SEARCHES",
            "account_id": config['account_id']
        }

        print("🔍 Fetching projects from LinkedIn API...")
        
        # Make request with retry logic
        for attempt in range(config['max_retries']):
            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=config['timeout']
                )
                response.raise_for_status()
                break
                
            except requests.exceptions.RequestException as e:
                if attempt == config['max_retries'] - 1:
                    raise e
                print(f"Request failed (attempt {attempt + 1}/{config['max_retries']}): {e}")
        
        # Parse response
        data = response.json()
        projects = []
        
        # Extract projects from response
        items = data.get('items', [])
        if not items:
            print("No items found in LinkedIn API response")
            return []
        
        for item in items:
            if item.get('object') == 'LinkedinSearchParameter':
                additional_data = item.get('additional_data', {})
                project_id = additional_data.get('project_id', '')
                
                if project_id:  # Only process items with valid project_id
                    project = {
                        'project_id': project_id,
                        'name': item.get('title', 'Unnamed Project'),
                        'title': item.get('title', ''),
                        'created_at': item.get('created_at', datetime.utcnow().isoformat() + "Z"),
                        'linkedin_search_id': item.get('id', ''),
                        'status': 'active',
                        'source': 'linkedin_api',
                        'details': item  # Full item data for reference
                    }
                    projects.append(project)
        
        print(f"✅ Successfully retrieved {len(projects)} projects from LinkedIn API")
        return projects
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching projects from LinkedIn API: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing LinkedIn API response: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error in get_projects_from_linkedin_api: {e}")
        return []


@tool
def get_projects_from_mongodb() -> List[Dict[str, Any]]:
    """Alternative tool to retrieve projects from MongoDB database.
    
    Returns:
        List[Dict[str, Any]]: A list of projects from MongoDB.
    """
    try:
        config = get_mongo_config()
        
        # Construct MongoDB URI
        uri = (
            f"mongodb+srv://{config['username']}:{config['password']}"
            f"@{config['host']}/{config['database']}"
            "?retryWrites=true&w=majority"
        )
        
        # Connect with timeout
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        
        # Test connection
        client.server_info()
        
        db = client[config['database']]
        collection = db[config['collection']]
        
        # Retrieve all active projects with standardized format
        query = {"status": {"$ne": "deleted"}}  # Exclude deleted projects
        projection = {'_id': 0}  # Exclude MongoDB _id field
        
        projects = []
        cursor = collection.find(query, projection)
        
        for doc in cursor:
            # Ensure consistent format
            project = {
                'project_id': doc.get('project_id', ''),
                'name': doc.get('title', doc.get('name', 'Unnamed Project')),
                'title': doc.get('title', ''),
                'created_at': doc.get('created_at', ''),
                'status': doc.get('status', 'active'),
                'source': 'mongodb',
                'details': doc  # Full document for reference
            }
            
            if project['project_id']:  # Only add projects with valid IDs
                projects.append(project)
        
        client.close()  # Clean up connection
        
        print(f" Successfully retrieved {len(projects)} projects from MongoDB")
        return projects
        
    except ValueError as e:
        print(f" Configuration error: {e}")
        return []
    except Exception as e:
        print(f" Error connecting to MongoDB: {e}")
        return []

@tool
def convert_project_to_json(project: Dict[str, Any]) -> Dict[str, Any]:
    """This tool converts a project dictionary into a standardized JSON format.
    
    Args:
        project (Dict[str, Any]): A dictionary containing project details.
        
    Returns:
        Dict[str, Any]: A standardized JSON representation of the project.
    """
    if not isinstance(project, dict):
        print("Warning: Project input is not a dictionary")
        return {}
    
    # Create standardized project format
    standardized = {
        "project_id": project.get("project_id", ""),
        "name": project.get("name") or project.get("title", "Unnamed Project"),
        "title": project.get("title", ""),
        "created_at": project.get("created_at", datetime.utcnow().isoformat() + "Z"),
        "status": project.get("status", "active"),
        "description": project.get("description", ""),
        "requirements": project.get("requirements", []),
        "skills_needed": project.get("skills_needed", []),
        "location": project.get("location", ""),
        "job_type": project.get("job_type", ""),
        "salary_range": project.get("salary_range", ""),
        "details": project  # Keep original data for reference
    }
    
    # Remove empty fields for cleaner output
    return {k: v for k, v in standardized.items() if v}

@tool
def get_all_projects(use_mongodb: bool = False, fallback: bool = True) -> List[Dict[str, Any]]:
    """Get projects from either LinkedIn API or MongoDB with optional fallback.
    
    Args:
        use_mongodb (bool): If True, try MongoDB first. If False, try LinkedIn API first.
        fallback (bool): If True, try the alternative source if the primary fails.
        
    Returns:
        List[Dict[str, Any]]: A list of projects from available source(s).
    """
    primary_source = "MongoDB" if use_mongodb else "LinkedIn API"
    secondary_source = "LinkedIn API" if use_mongodb else "MongoDB"
    
    print(f"🔄 Attempting to fetch projects from {primary_source}...")
    
    # Try primary source
    if use_mongodb:
        projects = get_projects_from_mongodb()
    else:
        projects = get_projects_from_linkedin_api()
    
    # If primary failed and fallback is enabled, try secondary
    if not projects and fallback:
        print(f" {primary_source} returned no results. Trying {secondary_source}...")
        
        if use_mongodb:
            projects = get_projects_from_linkedin_api()  # Try LinkedIn API as fallback
        else:
            projects = get_projects_from_mongodb()  # Try MongoDB as fallback
        
        if projects:
            print(f" Successfully retrieved {len(projects)} projects from {secondary_source} (fallback)")
    
    # Remove duplicates based on project_id if we somehow got any
    if projects:
        seen_ids = set()
        unique_projects = []
        for project in projects:
            project_id = project.get('project_id', '')
            if project_id and project_id not in seen_ids:
                seen_ids.add(project_id)
                unique_projects.append(project)
        
        if len(unique_projects) != len(projects):
            print(f"ℹRemoved {len(projects) - len(unique_projects)} duplicate projects")
        
        projects = unique_projects
    
    print(f"Final result: {len(projects)} unique projects available")
    return projects



