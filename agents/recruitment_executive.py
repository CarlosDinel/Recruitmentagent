"""This agent orchestrates the end-to-end recruitment process, from sourcing candidates to conducting interviews and making job offers.
It uses database agents to manage candidate information, outreach managers to handle communication with candidates, and profile scraping agents to gather detailed candidate profiles from various sources.

The RecruitmentExecutiveAgent is responsible for coordinating these sub-agents and ensuring a smooth and efficient recruitment workflow.
It can be configured with different recruitment strategies, candidate sourcing methods, and communication channels to suit the
specific needs of the organization.

The agent can also handle various recruitment scenarios, such as bulk hiring, specialized roles, and remote positions.
It can adapt its approach based on the requirements of each recruitment campaign and the preferences of the hiring managers.

The RecruitmentExecutiveAgent can be integrated with existing HR systems and recruitment platforms to streamline the hiring process and improve candidate experience.
It can also generate reports and analytics on recruitment metrics, such as time-to-hire, candidate quality, and source effectiveness.

Agent Identity

| Attribute           | Value                                                                 |
|---------------------|-----------------------------------------------------------------------|
| Name            | Executive Recruitment Orchestrator                                    |
| Primary Goal    | Break down user requests into atomic tasks and coordinate manager- and sub-agents to deliver complete, accurate recruitment outcomes. |
| Tone            | Concise, professional, supportive.                                    |
| Operating Hours | 24/7; scheduled triggers respect user-defined time zones.             |
"""

# ---- Package imports ----
from typing import List, Dict, Any, Optional, Sequence, Annotated
from datetime import datetime
import json
import logging
import os
import sys

# LangGraph and LangChain for agent framework
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.graph.message import add_messages
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

# Environment and configuration
from dotenv import load_dotenv
load_dotenv()

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your tools and other agents
from tools.get_projects import get_all_projects, convert_project_to_json
from state.agent_state import AgentState

from prompts.recruitment_executive_agent_prompts import RecruitmentPrompts

# NOTE: Circular import prevention - Import flows only when needed
# from flows.recruitment_executive_flow import RecruitmentExecutiveFlow

# agents imports
try:
    from agents.sourcing_manager_unified import UnifiedSourcingManager
except ImportError:
    UnifiedSourcingManager = None

try:
    from agents.database_agent import DatabaseAgent
except ImportError:
    DatabaseAgent = None

# Logging
logger = logging.getLogger('RecruitmentExecutiveAgent')
logging.basicConfig(level=logging.INFO)

# ---- Configuration ----
def get_ai_config():
    """Get AI model configuration from environment variables."""
    return {
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
        'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.3')),
        'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
    }

# ---- Recruitment Executive Agent State ----
class RecruitmentExecutiveState(TypedDict):
    """State for the Recruitment Executive Agent workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_request: str
    current_projects: List[Dict[str, Any]]
    active_campaigns: List[Dict[str, Any]]
    candidate_pipeline: Dict[str, List[Dict[str, Any]]]
    recruitment_strategy: str
    next_action: str
    reasoning: Optional[List[str]]
    human_review_required: Optional[bool]
    current_stage: Optional[str]
    processing_result: Optional[Dict[str, Any]]
    parsed_requirements: Optional[Dict[str, Any]]
    project_creation_result: Optional[Dict[str, Any]]


# ---- Example user request ----
EXAMPLE_USER_REQUEST = "Find and recruit a senior data scientist with expertise in machine learning and Python for our Amsterdam office."

# ---- Agent class structure ----
class RecruitmentExecutiveAgent:
    """The Recruitment Executive Agent orchestrates the recruitment process."""

    def __init__(self, state: Optional[RecruitmentExecutiveState] = None, config: Optional[Dict[str, Any]] = None):
        self.state = state or {
            'messages': [],
            'user_request': '',
            'current_projects': [],
            'active_campaigns': [],
            'candidate_pipeline': {},
            'recruitment_strategy': '',
            'next_action': '',
            'reasoning': None,
            'human_review_required': None,
            'current_stage': None,
            'processing_result': None,
            'parsed_requirements': None,
            'project_creation_result': None
        }
        self.config = config or get_ai_config()
        self.logger = logging.getLogger('RecruitmentExecutiveAgent')
        self.logger.setLevel(logging.DEBUG)
        
        # Lazy load managers to avoid circular imports
        self.sourcing_manager = None
        self.database_agent = None
        self._initialize_managers()
    
    def _initialize_managers(self):
        """Initialize manager agents if available."""
        try:
            if UnifiedSourcingManager:
                self.sourcing_manager = UnifiedSourcingManager(
                    model_name=self.config.get('model', 'gpt-4'),
                    temperature=self.config.get('temperature', 0.3)
                )
        except Exception as e:
            self.logger.warning(f"Could not initialize SourcingManager: {e}")
        
        try:
            if DatabaseAgent:
                self.database_agent = DatabaseAgent()
        except Exception as e:
            self.logger.warning(f"Could not initialize DatabaseAgent: {e}")


    def process_request_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Process a user recruitment request or LinkedIn project creation.
        
        This node handles two types of requests:
        1. Frontend user requests (direct recruitment needs)
        2. LinkedIn API project creation (via get_projects.py webhook)
        
        The node coordinates with Database Agent for all data operations.
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with processed request information
        """
        self.logger.info("Processing incoming request...")
        
        try:
            # Extract request information from state
            request_source = self._identify_request_source(state)
            request_data = self._extract_request_data(state)
            
            self.logger.info(f"Request source: {request_source}")
            self.logger.info(f"Request type: {request_data.get('type', 'unknown')}")
            
            # Process based on request source
            if request_source == "frontend_user":
                result = self._process_user_request(state, request_data)
            elif request_source == "linkedin_api":
                result = self._process_linkedin_project(state, request_data)
            else:
                result = self._handle_unknown_request(state, request_data)
            
            # Update state with processing results
            state['processing_result'] = result
            state['current_stage'] = 'request_processed'
            state['next_action'] = 'analyze_request'
            
            self.logger.info("Request processing completed")
            return state
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            state['next_action'] = 'error'
            state['reasoning'] = [f"Request processing failed: {str(e)}"]
            return state
    
    def _identify_request_source(self, state: RecruitmentExecutiveState) -> str:
        """Identify whether request comes from frontend user or LinkedIn API."""
        user_request = state.get('user_request', '')
        
        if not user_request:
            return 'unknown'
        
        # Check for LinkedIn API indicators
        linkedin_indicators = ['linkedin_search_id', 'saved_search', 'api_created', 'project_id', 'unipile']
        if any(indicator in str(user_request).lower() for indicator in linkedin_indicators):
            return 'linkedin_api'
        
        # Check for user request indicators
        return 'frontend_user'
    
    def _extract_request_data(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Extract and structure request data from state."""
        return {
            'type': 'user_request',
            'request': state.get('user_request', ''),
            'timestamp': datetime.now().isoformat()
        }
    
    def _process_user_request(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a frontend user recruitment request."""
        return {
            'status': 'processed',
            'request_type': 'user_recruitment_request',
            'parsed_data': request_data
        }
    
    def _process_linkedin_project(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a LinkedIn API project creation."""
        return {
            'status': 'processed',
            'request_type': 'linkedin_project_creation',
            'parsed_data': request_data
        }
    
    def _handle_unknown_request(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests of unknown type."""
        return {
            'status': 'unknown_request',
            'request_type': 'unknown',
            'parsed_data': request_data
        }
    
    async def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recruitment workflow."""
        self.state['user_request'] = request_data.get('request', '')
        result = self.process_request_node(self.state)
        return {
            'success': True,
            'result': result.get('processing_result', {}),
            'stage': result.get('current_stage')
        }
    
    def _identify_request_source(self, state: RecruitmentExecutiveState) -> str:
        """Identify whether request comes from frontend user or LinkedIn API.
        
        Args:
            state: Current state containing request information
            
        Returns:
            String indicating request source: 'frontend_user', 'linkedin_api', or 'unknown'
        """
        # Check messages for user input
        if state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'content') and last_message.content:
                # Check if it's a user request vs API data
                content = last_message.content.lower()
                
                # LinkedIn API indicators
                if any(indicator in content for indicator in [
                    "linkedin_search_id", "saved_search", "api_created", 
                    "project_id", "unipile", "linkedin_api"
                ]):
                    return "linkedin_api"
                
                # User request indicators
                if any(indicator in content for indicator in [
                    "find", "recruit", "hire", "looking for", "need", "search for"
                ]):
                    return "frontend_user"
        
        # Check for direct project data in state
        if state.get("linkedin_project_data"):
            return "linkedin_api"
        
        return "unknown"
    
    def _extract_request_data(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Extract and structure request data from state.
        
        Args:
            state: Current state
            
        Returns:
            Dictionary with structured request data
        """
        request_data = {
            "type": "unknown",
            "content": "",
            "timestamp": datetime.now().isoformat(),
            "project_data": None,
            "user_requirements": None
        }
        
        # Extract from messages
        if state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'content'):
                request_data["content"] = last_message.content
                
                # Try to parse as JSON for API requests
                try:
                    parsed_content = json.loads(last_message.content)
                    if isinstance(parsed_content, dict):
                        request_data["project_data"] = parsed_content
                        request_data["type"] = "linkedin_project"
                except json.JSONDecodeError:
                    # It's a user text request
                    request_data["user_requirements"] = last_message.content
                    request_data["type"] = "user_request"
        
        # Extract from direct state data
        if state.get("linkedin_project_data"):
            request_data["project_data"] = state["linkedin_project_data"]
            request_data["type"] = "linkedin_project"
        
        return request_data
    
    def _process_user_request(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a frontend user recruitment request.
        
        Args:
            state: Current state
            request_data: Extracted request information
            
        Returns:
            Dictionary with processing results
        """
        self.logger.info("👤 Processing frontend user request...")
        
        user_request = request_data.get("user_requirements", "")
        
        # Validate user request
        if not user_request or len(user_request.strip()) < 10:
            return {
                "processing_result": "validation_failed",
                "reasoning": ["User request is too short or empty"],
                "human_review_required": True,
                "user_request": [user_request]
            }
        
        # Parse user requirements using AI
        parsed_requirements = self._parse_user_requirements(user_request)
        
        # Check if we need to create a new project via Database Agent
        project_needed = self._assess_project_creation_need(parsed_requirements)
        
        result = {
            "processing_result": "user_request_processed",
            "user_request": [user_request],
            "parsed_requirements": parsed_requirements,
            "project_creation_needed": project_needed,
            "reasoning": [
                f"User request parsed successfully",
                f"Requirements extracted: {len(parsed_requirements)} items",
                f"Project creation needed: {project_needed}"
            ]
        }
        
        # If new project needed, delegate to Database Agent
        if project_needed:
            project_result = self._delegate_project_creation(parsed_requirements)
            result["project_creation_result"] = project_result
        
        return result
    
    def _process_linkedin_project(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a LinkedIn API project creation request.
        
        Args:
            state: Current state
            request_data: Project data from LinkedIn API
            
        Returns:
            Dictionary with processing results
        """
        self.logger.info("🔗 Processing LinkedIn API project...")
        
        project_data = request_data.get("project_data", {})
        
        # Validate LinkedIn project data
        validation_result = self._validate_linkedin_project(project_data)
        if not validation_result["valid"]:
            return {
                "processing_result": "validation_failed",
                "reasoning": validation_result["errors"],
                "human_review_required": True
            }
        
        # Transform LinkedIn data to internal project format
        internal_project = self._transform_linkedin_project(project_data)
        
        # Delegate project storage to Database Agent
        storage_result = self._delegate_project_storage(internal_project)
        
        result = {
            "processing_result": "linkedin_project_processed",
            "linkedin_project_data": project_data,
            "internal_project_data": internal_project,
            "storage_result": storage_result,
            "reasoning": [
                "LinkedIn project data validated",
                "Project transformed to internal format",
                f"Storage result: {storage_result.get('success', False)}"
            ]
        }
        
        return result
    
    def _handle_unknown_request(self, state: RecruitmentExecutiveState, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests that don't match expected patterns.
        
        Args:
            state: Current state
            request_data: Request information
            
        Returns:
            Dictionary with error handling results
        """
        self.logger.warning("⚠️ Unknown request type received")
        
        return {
            "processing_result": "unknown_request",
            "reasoning": [
                "Request type could not be determined",
                "Manual review required to classify request",
                f"Content preview: {str(request_data.get('content', ''))[:100]}..."
            ],
            "human_review_required": True,
            "raw_request_data": request_data
        }
    
    def _parse_user_requirements(self, user_request: str) -> Dict[str, Any]:
        """Parse user requirements using AI to extract structured information.
        
        Args:
            user_request: Raw user request string
            
        Returns:
            Dictionary with parsed requirements
        """
        # Simple parsing logic (can be enhanced with LLM)
        requirements = {
            "position": "",
            "skills": [],
            "location": "",
            "experience_level": "",
            "urgency": "normal",
            "quantity": 1,
            "raw_request": user_request
        }
        
        request_lower = user_request.lower()
        
        # Extract position
        position_keywords = ["developer", "engineer", "scientist", "manager", "analyst", "designer"]
        for keyword in position_keywords:
            if keyword in request_lower:
                requirements["position"] = keyword.title()
                break
        
        # Extract skills
        skill_keywords = ["python", "javascript", "react", "django", "sql", "machine learning", "aws", "docker"]
        for skill in skill_keywords:
            if skill in request_lower:
                requirements["skills"].append(skill.title())
        
        # Extract location
        location_keywords = ["amsterdam", "rotterdam", "utrecht", "remote", "hybrid"]
        for location in location_keywords:
            if location in request_lower:
                requirements["location"] = location.title()
                break
        
        # Extract urgency
        if any(word in request_lower for word in ["urgent", "asap", "immediately"]):
            requirements["urgency"] = "urgent"
        
        return requirements
    
    def _assess_project_creation_need(self, requirements: Dict[str, Any]) -> bool:
        """Assess if a new project needs to be created for this request.
        
        Args:
            requirements: Parsed user requirements
            
        Returns:
            Boolean indicating if new project creation is needed
        """
        # Check if we have enough information for a project
        has_position = bool(requirements.get("position"))
        has_location = bool(requirements.get("location"))
        
        # Always create project for new user requests with basic info
        return has_position or has_location
    
    def _delegate_project_creation(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate project creation to Database Agent.
        
        Args:
            requirements: Parsed user requirements
            
        Returns:
            Dictionary with project creation results
        """
        self.logger.info("📤 Delegating project creation to Database Agent...")
        
        try:
            # Import Database Agent (avoid circular imports)
            from agents.database_agent import DatabaseAgent
            
            # Initialize Database Agent
            db_agent = DatabaseAgent()
            
            # Prepare project data
            project_data = {
                "title": f"{requirements.get('position', 'Position')} - {requirements.get('location', 'Location')}",
                "project_id": f"REQ-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "company": "Internal Request",
                "description": requirements.get("raw_request", ""),
                "requirements": requirements.get("raw_request", ""),
                "skills_needed": requirements.get("skills", []),
                "location": requirements.get("location", ""),
                "job_type": "Full-time",
                "status": "active",
                "urgency": requirements.get("urgency", "normal"),
                "source": "frontend_user"
            }
            
            # Validate project structure first
            validation_result = db_agent.execute_tool("validate_project_structure", project_data=project_data)
            
            if not validation_result.get("valid", False):
                return {
                    "success": False,
                    "error": validation_result.get("error", "Project validation failed"),
                    "message": "Project data validation failed"
                }
            
            # Create project via Database Agent
            creation_result = db_agent.execute_tool("create_project", project_data=project_data)
            
            self.logger.info(f"📋 Project creation result: {creation_result.get('success', False)}")
            return creation_result
            
        except Exception as e:
            self.logger.error(f"❌ Project creation delegation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delegate project creation"
            }
    
    def _validate_linkedin_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate LinkedIn project data structure.
        
        Args:
            project_data: Raw LinkedIn project data
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        
        # Check required LinkedIn fields
        required_fields = ["id", "title"]
        for field in required_fields:
            if not project_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check data types
        if project_data.get("title") and not isinstance(project_data["title"], str):
            errors.append("Title must be a string")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _transform_linkedin_project(self, linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform LinkedIn project data to internal project format.
        
        Args:
            linkedin_data: Raw LinkedIn project data
            
        Returns:
            Dictionary in internal project format
        """
        # Extract additional data if present
        additional_data = linkedin_data.get("additional_data", {})
        
        return {
            "title": linkedin_data.get("title", "LinkedIn Project"),
            "project_id": linkedin_data.get("id", f"LI-{datetime.now().strftime('%Y%m%d-%H%M%S')}"),
            "company": additional_data.get("company", "LinkedIn Source"),
            "description": linkedin_data.get("description", "Project created via LinkedIn API"),
            "requirements": additional_data.get("requirements", ""),
            "skills_needed": additional_data.get("skills", []),
            "location": additional_data.get("location", ""),
            "job_type": additional_data.get("job_type", "Full-time"),
            "status": "active",
            "urgency": additional_data.get("urgency", "normal"),
            "source": "linkedin_api",
            "linkedin_search_id": linkedin_data.get("id", ""),
            "linkedin_search_parameters": linkedin_data
        }
    
    def _delegate_project_storage(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate project storage to Database Agent.
        
        Args:
            project_data: Internal project data to store
            
        Returns:
            Dictionary with storage results
        """
        self.logger.info("📤 Delegating project storage to Database Agent...")
        
        try:
            # Import Database Agent
            from agents.database_agent import DatabaseAgent
            
            # Initialize Database Agent
            db_agent = DatabaseAgent()
            
            # Store project via Database Agent
            storage_result = db_agent.execute_tool("create_project", project_data=project_data)
            
            self.logger.info(f"💾 Project storage result: {storage_result.get('success', False)}")
            return storage_result
            
        except Exception as e:
            self.logger.error(f"❌ Project storage delegation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delegate project storage"
            }

    def analyze_request_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Analyze the user request and extract requirements."""
        logger.info(" Analyzing user request...")
        
        # Get the user request from messages
        user_request = ""
        if state.get("messages"):
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                user_request = last_message.content
        
        # Use the recruitment prompt
        prompt = RecruitmentPrompts.user_request_prompt(user_request)
        
        # Process with LLM
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Update state
        state["user_request"] = [user_request]
        state["next_action"] = "get_projects"
        
        # Add AI response to messages
        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(response)
        
        logger.info("Request analysis completed")
        return state
    
    def get_projects_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Retrieve relevant projects from the database."""
        logger.info(" Retrieving projects...")
        
        try:
            # Get all projects with fallback
            projects = get_all_projects(use_mongodb=False, fallback=True)
            
            # Convert to standardized format
            formatted_projects = [convert_project_to_json(project) for project in projects]
            
            state["current_projects"] = formatted_projects
            state["next_action"] = "plan_strategy"
            
            logger.info(f" Retrieved {len(formatted_projects)} projects")
            
        except Exception as e:
            logger.error(f" Error retrieving projects: {e}")
            state["current_projects"] = []
            state["next_action"] = "plan_strategy"
        
        return state
    
    def plan_strategy_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Plan the recruitment strategy based on request and available projects."""
        logger.info("Planning recruitment strategy...")
        
        user_request = state.get("user_request", [""])[0] if state.get("user_request") else ""
        projects = state.get("current_projects", [])
        
        # Simple strategy planning (can be enhanced with LLM)
        if "urgent" in user_request.lower():
            strategy = "fast_track"
            next_action = "sourcing"
        elif "bulk" in user_request.lower() or any(str(i) in user_request for i in range(2, 20)):
            strategy = "bulk_hiring"
            next_action = "sourcing"
        else:
            strategy = "standard_recruitment"
            next_action = "sourcing"
        
        state["recruitment_strategy"] = strategy
        state["next_action"] = next_action
        
        # Initialize candidate pipeline
        if not state.get("candidate_pipeline"):
            state["candidate_pipeline"] = {
                "sourced": [],
                "contacted": [],
                "responded": [],
                "interviewed": [],
                "hired": []
            }
        
        logger.info(f" Strategy planned: {strategy}")
        return state
    
    def delegate_sourcing_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Delegate sourcing tasks to the Sourcing Manager.
        
        This node coordinates with the SourcingManager to find candidates based on:
        - Parsed requirements from user request
        - Available projects in the database
        - Current recruitment strategy
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with sourcing results
        """
        self.logger.info("🔍 Delegating to Sourcing Manager...")
        
        try:
            # Extract information needed for sourcing
            sourcing_requirements = self._prepare_sourcing_requirements(state)
            
            # Delegate to Sourcing Manager
            sourcing_results = self._delegate_to_sourcing_manager(sourcing_requirements)
            
            # Process and validate sourcing results
            processed_results = self._process_sourcing_results(sourcing_results)
            
            # Update candidate pipeline with sourced candidates
            if not state.get("candidate_pipeline"):
                state["candidate_pipeline"] = {
                    "sourced": [],
                    "contacted": [],
                    "responded": [],
                    "interviewed": [],
                    "hired": []
                }
            
            state["candidate_pipeline"]["sourced"] = processed_results.get("candidates", [])
            state["sourcing_status"] = processed_results.get("status", "completed")
            state["sourcing_metrics"] = processed_results.get("metrics", {})
            
            # Determine next action based on sourcing results
            if processed_results.get("success", False) and len(processed_results.get("candidates", [])) > 0:
                state["next_action"] = "outreach"
                state["reasoning"] = [
                    f"Sourcing completed successfully",
                    f"Found {len(processed_results.get('candidates', []))} candidates",
                    "Proceeding to outreach phase"
                ]
            else:
                state["next_action"] = "sourcing_review"
                state["human_review_required"] = True
                state["reasoning"] = [
                    "Sourcing completed but with limited results",
                    "Human review required to adjust strategy"
                ]
            
            self.logger.info(f"✅ Sourcing delegation completed: {len(processed_results.get('candidates', []))} candidates found")
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Sourcing delegation failed: {e}")
            state["next_action"] = "error"
            state["sourcing_status"] = "failed"
            state["reasoning"] = [f"Sourcing delegation failed: {str(e)}"]
            return state
    
    def delegate_outreach_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Delegate outreach tasks to the Outreach Manager.
        
        This node coordinates with the OutreachManager to contact candidates:
        - Prioritizes candidates based on fit score
        - Manages multi-channel outreach (LinkedIn, Email, InMail)
        - Tracks response rates and engagement
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with outreach results
        """
        self.logger.info("📤 Delegating to Outreach Manager...")
        
        try:
            # Prepare outreach campaign data
            outreach_campaign = self._prepare_outreach_campaign(state)
            
            # Delegate to Outreach Manager
            outreach_results = self._delegate_to_outreach_manager(outreach_campaign)
            
            # Process outreach results
            processed_outreach = self._process_outreach_results(outreach_results)
            
            # Update candidate pipeline
            pipeline = state.get("candidate_pipeline", {})
            pipeline["contacted"] = processed_outreach.get("contacted_candidates", [])
            pipeline["responded"] = processed_outreach.get("responded_candidates", [])
            
            # Update outreach metrics
            state["outreach_status"] = processed_outreach.get("status", "in_progress")
            state["outreach_metrics"] = processed_outreach.get("metrics", {})
            state["active_campaigns"] = processed_outreach.get("campaigns", [])
            
            # Determine next action
            if processed_outreach.get("requires_monitoring", True):
                state["next_action"] = "monitor"
                state["reasoning"] = [
                    "Outreach campaign initiated",
                    f"Contacted {len(processed_outreach.get('contacted_candidates', []))} candidates",
                    "Entering monitoring phase for responses"
                ]
            else:
                state["next_action"] = "complete"
                state["reasoning"] = [
                    "Outreach campaign completed",
                    "No monitoring required"
                ]
            
            self.logger.info(f"✅ Outreach delegation completed: {len(processed_outreach.get('contacted_candidates', []))} candidates contacted")
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Outreach delegation failed: {e}")
            state["next_action"] = "error"
            state["outreach_status"] = "failed"
            state["reasoning"] = [f"Outreach delegation failed: {str(e)}"]
            return state
    
    def monitor_progress_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Monitor the progress of the recruitment campaign.
        
        This node continuously monitors:
        - Sourcing Manager progress and results
        - Outreach Manager campaign performance
        - Candidate pipeline progression
        - Overall recruitment metrics
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with monitoring results
        """
        self.logger.info("📊 Monitoring recruitment progress...")
        
        try:
            # Monitor sourcing progress
            sourcing_status = self._monitor_sourcing_progress(state)
            
            # Monitor outreach progress
            outreach_status = self._monitor_outreach_progress(state)
            
            # Calculate overall progress metrics
            progress_metrics = self._calculate_progress_metrics(state, sourcing_status, outreach_status)
            
            # Update state with monitoring results
            state["monitoring_results"] = {
                "sourcing_status": sourcing_status,
                "outreach_status": outreach_status,
                "progress_metrics": progress_metrics,
                "last_monitored": datetime.now().isoformat()
            }
            
            # Determine if intervention is needed
            intervention_needed = self._assess_intervention_need(progress_metrics)
            
            if intervention_needed:
                state["next_action"] = "intervention"
                state["human_review_required"] = True
                state["reasoning"] = [
                    "Monitoring detected issues requiring intervention",
                    f"Sourcing status: {sourcing_status.get('status', 'unknown')}",
                    f"Outreach status: {outreach_status.get('status', 'unknown')}"
                ]
            elif self._should_continue_monitoring(progress_metrics):
                state["next_action"] = "monitor"
                state["reasoning"] = [
                    "Monitoring continues - campaign in progress",
                    f"Response rate: {progress_metrics.get('response_rate', 0):.1f}%",
                    f"Pipeline health: {progress_metrics.get('pipeline_health', 'unknown')}"
                ]
            else:
                state["next_action"] = "complete"
                state["reasoning"] = [
                    "Monitoring completed - campaign objectives met",
                    f"Total candidates sourced: {progress_metrics.get('total_sourced', 0)}",
                    f"Total responses: {progress_metrics.get('total_responded', 0)}"
                ]
            
            self.logger.info(f"📈 Monitoring completed: {progress_metrics.get('pipeline_health', 'unknown')} pipeline health")
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Monitoring failed: {e}")
            state["next_action"] = "error"
            state["reasoning"] = [f"Progress monitoring failed: {str(e)}"]
            return state
    
    
    # ---- Manager Delegation Helper Methods ----
    
    def _prepare_sourcing_requirements(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Prepare requirements data for the Sourcing Manager.
        
        Args:
            state: Current recruitment state
            
        Returns:
            Dictionary with sourcing requirements
        """
        # Extract parsed requirements
        parsed_reqs = state.get("parsed_requirements", {})
        current_projects = state.get("current_projects", [])
        
        sourcing_requirements = {
            "position": parsed_reqs.get("position", ""),
            "skills": parsed_reqs.get("skills", []),
            "location": parsed_reqs.get("location", ""),
            "experience_level": parsed_reqs.get("experience_level", ""),
            "urgency": parsed_reqs.get("urgency", "normal"),
            "quantity": parsed_reqs.get("quantity", 5),  # Default to 5 candidates
            "projects": current_projects,
            "strategy": state.get("recruitment_strategy", "standard_recruitment"),
            "budget_constraints": {
                "max_candidates_to_source": 20,
                "preferred_sources": ["linkedin", "github", "referrals"]
            }
        }
        
        return sourcing_requirements
    
    def _delegate_to_sourcing_manager(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate sourcing tasks to the Sourcing Manager Agent.
        
        Args:
            requirements: Sourcing requirements dictionary
            
        Returns:
            Dictionary with sourcing results
        """
        try:
            self.logger.info("📤 Initiating Sourcing Manager delegation...")
            
            # Import Sourcing Manager (avoid circular imports)
            from agents.scourcing_manager import SourcingManagerAgent
            
            # Initialize Sourcing Manager
            sourcing_manager = SourcingManagerAgent()
            
            # Execute sourcing workflow
            sourcing_result = sourcing_manager.execute_sourcing_workflow(requirements)
            
            self.logger.info(f"📊 Sourcing Manager returned: {sourcing_result.get('status', 'unknown')}")
            return sourcing_result
            
        except ImportError:
            # Fallback if SourcingManager not implemented yet
            self.logger.warning("⚠️ SourcingManager not available, using mock results")
            return self._mock_sourcing_results(requirements)
        except Exception as e:
            self.logger.error(f"❌ Sourcing Manager delegation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "candidates": [],
                "status": "failed"
            }
    
    def _mock_sourcing_results(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock sourcing results for testing purposes.
        
        Args:
            requirements: Sourcing requirements
            
        Returns:
            Mock sourcing results
        """
        position = requirements.get("position", "Developer")
        skills = requirements.get("skills", ["Python"])
        location = requirements.get("location", "Amsterdam")
        quantity = requirements.get("quantity", 5)
        
        mock_candidates = []
        for i in range(min(quantity, 3)):  # Generate up to 3 mock candidates
            candidate = {
                "name": f"Candidate {i+1}",
                "email": f"candidate{i+1}@example.com",
                "position": f"Senior {position}",
                "skills": skills + [f"Skill{i+1}"],
                "experience": f"{3+i} years",
                "location": location,
                "source": "mock_linkedin",
                "fit_score": 85 - (i * 5),
                "availability": "Available",
                "contact_info": {
                    "linkedin": f"linkedin.com/in/candidate{i+1}",
                    "phone": f"+31 6 1234 567{i}"
                }
            }
            mock_candidates.append(candidate)
        
        return {
            "success": True,
            "candidates": mock_candidates,
            "status": "completed",
            "metrics": {
                "total_searched": quantity * 10,
                "total_found": len(mock_candidates),
                "average_fit_score": sum(c["fit_score"] for c in mock_candidates) / len(mock_candidates) if mock_candidates else 0,
                "sources_used": ["linkedin", "github"],
                "search_duration": "2.5 hours"
            }
        }
    
    def _process_sourcing_results(self, sourcing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate sourcing results from Sourcing Manager.
        
        Args:
            sourcing_results: Raw results from Sourcing Manager
            
        Returns:
            Processed and validated results
        """
        candidates = sourcing_results.get("candidates", [])
        
        # Validate and enrich candidate data
        processed_candidates = []
        for candidate in candidates:
            if self._validate_candidate_data(candidate):
                # Enrich with additional metadata
                enriched_candidate = {
                    **candidate,
                    "sourced_at": datetime.now().isoformat(),
                    "status": "sourced",
                    "pipeline_stage": "sourced",
                    "next_action": "outreach"
                }
                processed_candidates.append(enriched_candidate)
        
        return {
            "success": len(processed_candidates) > 0,
            "candidates": processed_candidates,
            "status": "completed" if processed_candidates else "low_results",
            "metrics": sourcing_results.get("metrics", {}),
            "quality_score": self._calculate_candidate_quality_score(processed_candidates)
        }
    
    def _validate_candidate_data(self, candidate: Dict[str, Any]) -> bool:
        """Validate individual candidate data structure.
        
        Args:
            candidate: Candidate data dictionary
            
        Returns:
            Boolean indicating if candidate data is valid
        """
        required_fields = ["name", "email", "skills"]
        return all(candidate.get(field) for field in required_fields)
    
    def _calculate_candidate_quality_score(self, candidates: List[Dict[str, Any]]) -> float:
        """Calculate overall quality score for sourced candidates.
        
        Args:
            candidates: List of candidate dictionaries
            
        Returns:
            Quality score between 0-100
        """
        if not candidates:
            return 0.0
        
        total_score = 0
        for candidate in candidates:
            # Base score from fit_score
            score = candidate.get("fit_score", 50)
            
            # Bonus for complete contact info
            if candidate.get("contact_info", {}).get("linkedin"):
                score += 10
            if candidate.get("contact_info", {}).get("phone"):
                score += 5
            
            # Bonus for availability
            if candidate.get("availability") == "Available":
                score += 10
            
            total_score += min(score, 100)  # Cap at 100
        
        return total_score / len(candidates)
    
    def _prepare_outreach_campaign(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Prepare outreach campaign data for the Outreach Manager.
        
        Args:
            state: Current recruitment state
            
        Returns:
            Dictionary with outreach campaign configuration
        """
        candidates = state.get("candidate_pipeline", {}).get("sourced", [])
        parsed_reqs = state.get("parsed_requirements", {})
        
        campaign_config = {
            "candidates": candidates,
            "campaign_name": f"Recruitment_{datetime.now().strftime('%Y%m%d_%H%M')}",
            "position_details": {
                "title": parsed_reqs.get("position", "Position"),
                "location": parsed_reqs.get("location", ""),
                "urgency": parsed_reqs.get("urgency", "normal")
            },
            "outreach_strategy": {
                "primary_channel": "linkedin",
                "secondary_channel": "email",
                "personalization_level": "high",
                "follow_up_sequence": True,
                "max_attempts": 3
            },
            "message_templates": {
                "initial_contact": "professional_introduction",
                "follow_up": "gentle_reminder",
                "final_attempt": "last_chance"
            },
            "timing": {
                "send_immediately": state.get("recruitment_strategy") == "fast_track",
                "business_hours_only": True,
                "timezone": "Europe/Amsterdam"
            }
        }
        
        return campaign_config
    
    def _delegate_to_outreach_manager(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate outreach tasks to the Outreach Manager Agent.
        
        Args:
            campaign_config: Outreach campaign configuration
            
        Returns:
            Dictionary with outreach results
        """
        try:
            self.logger.info("📤 Initiating Outreach Manager delegation...")
            
            # Import Outreach Manager (avoid circular imports)
            from agents.outreach_manager import OutreachManagerAgent
            
            # Initialize Outreach Manager
            outreach_manager = OutreachManagerAgent()
            
            # Execute outreach campaign
            outreach_result = outreach_manager.execute_outreach_campaign(campaign_config)
            
            self.logger.info(f"📊 Outreach Manager returned: {outreach_result.get('status', 'unknown')}")
            return outreach_result
            
        except ImportError:
            # Fallback if OutreachManager not implemented yet
            self.logger.warning("⚠️ OutreachManager not available, using mock results")
            return self._mock_outreach_results(campaign_config)
        except Exception as e:
            self.logger.error(f"❌ Outreach Manager delegation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "contacted_candidates": [],
                "status": "failed"
            }
    
    def _mock_outreach_results(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock outreach results for testing purposes.
        
        Args:
            campaign_config: Campaign configuration
            
        Returns:
            Mock outreach results
        """
        candidates = campaign_config.get("candidates", [])
        
        # Simulate contacting candidates
        contacted_candidates = []
        responded_candidates = []
        
        for i, candidate in enumerate(candidates):
            # Add outreach status to candidate
            contacted_candidate = {
                **candidate,
                "contacted_at": datetime.now().isoformat(),
                "contact_method": "linkedin",
                "message_sent": True,
                "outreach_status": "contacted"
            }
            contacted_candidates.append(contacted_candidate)
            
            # Simulate some responses (30% response rate)
            if i < len(candidates) * 0.3:
                responded_candidate = {
                    **contacted_candidate,
                    "responded_at": datetime.now().isoformat(),
                    "response_type": "positive",
                    "outreach_status": "responded"
                }
                responded_candidates.append(responded_candidate)
        
        return {
            "success": True,
            "contacted_candidates": contacted_candidates,
            "responded_candidates": responded_candidates,
            "status": "in_progress",
            "campaigns": [{
                "campaign_id": campaign_config.get("campaign_name", "mock_campaign"),
                "status": "active",
                "total_sent": len(contacted_candidates),
                "total_responded": len(responded_candidates),
                "response_rate": (len(responded_candidates) / len(contacted_candidates) * 100) if contacted_candidates else 0
            }],
            "metrics": {
                "total_contacted": len(contacted_candidates),
                "total_responded": len(responded_candidates),
                "response_rate": (len(responded_candidates) / len(contacted_candidates) * 100) if contacted_candidates else 0,
                "channels_used": ["linkedin", "email"],
                "campaign_duration": "2 days"
            },
            "requires_monitoring": True
        }
    
    def _process_outreach_results(self, outreach_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate outreach results from Outreach Manager.
        
        Args:
            outreach_results: Raw results from Outreach Manager
            
        Returns:
            Processed and validated results
        """
        contacted = outreach_results.get("contacted_candidates", [])
        responded = outreach_results.get("responded_candidates", [])
        
        # Process contacted candidates
        processed_contacted = []
        for candidate in contacted:
            processed_candidate = {
                **candidate,
                "pipeline_stage": "contacted",
                "last_contact": candidate.get("contacted_at", datetime.now().isoformat())
            }
            processed_contacted.append(processed_candidate)
        
        # Process responded candidates
        processed_responded = []
        for candidate in responded:
            processed_candidate = {
                **candidate,
                "pipeline_stage": "responded",
                "engagement_score": self._calculate_engagement_score(candidate)
            }
            processed_responded.append(processed_candidate)
        
        return {
            "success": len(processed_contacted) > 0,
            "contacted_candidates": processed_contacted,
            "responded_candidates": processed_responded,
            "status": outreach_results.get("status", "completed"),
            "campaigns": outreach_results.get("campaigns", []),
            "metrics": outreach_results.get("metrics", {}),
            "requires_monitoring": outreach_results.get("requires_monitoring", False)
        }
    
    def _calculate_engagement_score(self, candidate: Dict[str, Any]) -> int:
        """Calculate engagement score for a candidate based on response.
        
        Args:
            candidate: Candidate with response data
            
        Returns:
            Engagement score between 0-100
        """
        base_score = 50
        
        # Response type bonus
        response_type = candidate.get("response_type", "neutral")
        if response_type == "positive":
            base_score += 30
        elif response_type == "interested":
            base_score += 40
        elif response_type == "very_interested":
            base_score += 50
        
        # Response speed bonus
        contacted_at = candidate.get("contacted_at")
        responded_at = candidate.get("responded_at")
        if contacted_at and responded_at:
            # Quick response bonus (within 24 hours)
            time_diff = datetime.fromisoformat(responded_at.replace('Z', '+00:00')) - datetime.fromisoformat(contacted_at.replace('Z', '+00:00'))
            if time_diff.total_seconds() < 86400:  # 24 hours
                base_score += 10
        
        return min(base_score, 100)
    
    # ---- Progress Monitoring Methods ----
    
    def _monitor_sourcing_progress(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Monitor progress of sourcing operations.
        
        Args:
            state: Current recruitment state
            
        Returns:
            Dictionary with sourcing progress status
        """
        sourcing_metrics = state.get("sourcing_metrics", {})
        sourced_candidates = state.get("candidate_pipeline", {}).get("sourced", [])
        
        status = {
            "status": state.get("sourcing_status", "unknown"),
            "total_sourced": len(sourced_candidates),
            "quality_score": sourcing_metrics.get("average_fit_score", 0),
            "completion_rate": 100 if state.get("sourcing_status") == "completed" else 75,
            "issues": []
        }
        
        # Check for issues
        if len(sourced_candidates) < 2:
            status["issues"].append("Low candidate volume")
        if sourcing_metrics.get("average_fit_score", 0) < 70:
            status["issues"].append("Low candidate quality scores")
        
        return status
    
    def _monitor_outreach_progress(self, state: RecruitmentExecutiveState) -> Dict[str, Any]:
        """Monitor progress of outreach operations.
        
        Args:
            state: Current recruitment state
            
        Returns:
            Dictionary with outreach progress status
        """
        outreach_metrics = state.get("outreach_metrics", {})
        campaigns = state.get("active_campaigns", [])
        
        contacted = len(state.get("candidate_pipeline", {}).get("contacted", []))
        responded = len(state.get("candidate_pipeline", {}).get("responded", []))
        
        response_rate = (responded / contacted * 100) if contacted > 0 else 0
        
        status = {
            "status": state.get("outreach_status", "unknown"),
            "total_contacted": contacted,
            "total_responded": responded,
            "response_rate": response_rate,
            "active_campaigns": len(campaigns),
            "issues": []
        }
        
        # Check for issues
        if response_rate < 10:
            status["issues"].append("Low response rate")
        if contacted == 0:
            status["issues"].append("No outreach initiated")
        
        return status
    
    def _calculate_progress_metrics(self, state: RecruitmentExecutiveState, sourcing_status: Dict[str, Any], outreach_status: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall progress metrics for the recruitment campaign.
        
        Args:
            state: Current recruitment state
            sourcing_status: Sourcing progress status
            outreach_status: Outreach progress status
            
        Returns:
            Dictionary with comprehensive progress metrics
        """
        pipeline = state.get("candidate_pipeline", {})
        
        metrics = {
            "total_sourced": len(pipeline.get("sourced", [])),
            "total_contacted": len(pipeline.get("contacted", [])),
            "total_responded": len(pipeline.get("responded", [])),
            "total_interviewed": len(pipeline.get("interviewed", [])),
            "total_hired": len(pipeline.get("hired", [])),
            "response_rate": outreach_status.get("response_rate", 0),
            "conversion_funnel": {
                "sourced_to_contacted": (len(pipeline.get("contacted", [])) / len(pipeline.get("sourced", [])) * 100) if pipeline.get("sourced") else 0,
                "contacted_to_responded": outreach_status.get("response_rate", 0),
                "responded_to_interviewed": (len(pipeline.get("interviewed", [])) / len(pipeline.get("responded", [])) * 100) if pipeline.get("responded") else 0
            },
            "pipeline_health": self._assess_pipeline_health(pipeline, sourcing_status, outreach_status),
            "campaign_duration": self._calculate_campaign_duration(state),
            "quality_metrics": {
                "sourcing_quality": sourcing_status.get("quality_score", 0),
                "engagement_quality": self._calculate_average_engagement(pipeline.get("responded", []))
            }
        }
        
        return metrics
    
    def _assess_pipeline_health(self, pipeline: Dict[str, List], sourcing_status: Dict[str, Any], outreach_status: Dict[str, Any]) -> str:
        """Assess overall health of the recruitment pipeline.
        
        Args:
            pipeline: Candidate pipeline data
            sourcing_status: Sourcing status
            outreach_status: Outreach status
            
        Returns:
            Health status: 'excellent', 'good', 'fair', 'poor'
        """
        sourced = len(pipeline.get("sourced", []))
        responded = len(pipeline.get("responded", []))
        response_rate = outreach_status.get("response_rate", 0)
        quality_score = sourcing_status.get("quality_score", 0)
        
        # Health scoring
        health_score = 0
        
        # Volume scoring
        if sourced >= 5:
            health_score += 25
        elif sourced >= 3:
            health_score += 15
        elif sourced >= 1:
            health_score += 5
        
        # Response rate scoring
        if response_rate >= 20:
            health_score += 25
        elif response_rate >= 10:
            health_score += 15
        elif response_rate >= 5:
            health_score += 5
        
        # Quality scoring
        if quality_score >= 80:
            health_score += 25
        elif quality_score >= 70:
            health_score += 15
        elif quality_score >= 60:
            health_score += 5
        
        # Progress scoring
        if responded > 0:
            health_score += 25
        
        # Determine health status
        if health_score >= 80:
            return "excellent"
        elif health_score >= 60:
            return "good"
        elif health_score >= 40:
            return "fair"
        else:
            return "poor"
    
    def _calculate_campaign_duration(self, state: RecruitmentExecutiveState) -> str:
        """Calculate duration of the recruitment campaign.
        
        Args:
            state: Current recruitment state
            
        Returns:
            Campaign duration as string
        """
        # This would be calculated from campaign start time
        # For now, return a placeholder
        return "2 days"
    
    def _calculate_average_engagement(self, responded_candidates: List[Dict[str, Any]]) -> float:
        """Calculate average engagement score for responded candidates.
        
        Args:
            responded_candidates: List of candidates who responded
            
        Returns:
            Average engagement score
        """
        if not responded_candidates:
            return 0.0
        
        total_engagement = sum(candidate.get("engagement_score", 50) for candidate in responded_candidates)
        return total_engagement / len(responded_candidates)
    
    def _assess_intervention_need(self, progress_metrics: Dict[str, Any]) -> bool:
        """Assess if human intervention is needed based on progress metrics.
        
        Args:
            progress_metrics: Comprehensive progress metrics
            
        Returns:
            Boolean indicating if intervention is needed
        """
        pipeline_health = progress_metrics.get("pipeline_health", "poor")
        response_rate = progress_metrics.get("response_rate", 0)
        total_sourced = progress_metrics.get("total_sourced", 0)
        
        # Intervention triggers
        if pipeline_health == "poor":
            return True
        if response_rate < 5 and progress_metrics.get("total_contacted", 0) > 5:
            return True
        if total_sourced < 2:
            return True
        
        return False
    
    def _should_continue_monitoring(self, progress_metrics: Dict[str, Any]) -> bool:
        """Determine if monitoring should continue.
        
        Args:
            progress_metrics: Current progress metrics
            
        Returns:
            Boolean indicating if monitoring should continue
        """
        # Continue monitoring if campaign is active and healthy
        pipeline_health = progress_metrics.get("pipeline_health", "poor")
        total_responded = progress_metrics.get("total_responded", 0)
        
        # Stop monitoring if we have enough responses or campaign is complete
        if total_responded >= 3:  # Sufficient responses
            return False
        if pipeline_health in ["excellent", "good"] and total_responded > 0:
            return True
        if pipeline_health == "poor":
           return True
    
    def generate_report_node(self, state: RecruitmentExecutiveState) -> RecruitmentExecutiveState:
        """Generate comprehensive recruitment campaign report.
        
        Args:
            state: Current recruitment executive state
            
        Returns:
            Updated state with generated report
        """
        self.logger.info("📊 Generating comprehensive recruitment report...")
        
        try:
            # Get current pipeline data
            pipeline = state.get("candidate_pipeline", {})
            sourcing_metrics = state.get("sourcing_metrics", {})
            outreach_metrics = state.get("outreach_metrics", {})
            monitoring_results = state.get("monitoring_results", {})
            
            # Calculate summary statistics
            summary_stats = {
                "total_sourced": len(pipeline.get("sourced", [])),
                "total_contacted": len(pipeline.get("contacted", [])),
                "total_responded": len(pipeline.get("responded", [])),
                "total_interviewed": len(pipeline.get("interviewed", [])),
                "total_hired": len(pipeline.get("hired", []))
            }
            
            # Calculate conversion rates
            conversion_rates = {
                "sourced_to_contacted": self._safe_percentage(summary_stats["total_contacted"], summary_stats["total_sourced"]),
                "contacted_to_responded": self._safe_percentage(summary_stats["total_responded"], summary_stats["total_contacted"]),
                "responded_to_interviewed": self._safe_percentage(summary_stats["total_interviewed"], summary_stats["total_responded"]),
                "interviewed_to_hired": self._safe_percentage(summary_stats["total_hired"], summary_stats["total_interviewed"])
            }
            
            # Generate detailed report
            report = {
                "report_id": f"recruitment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "generated_at": datetime.now().isoformat(),
                "campaign_summary": {
                    "position": state.get("parsed_requirements", {}).get("position", "N/A"),
                    "duration": self._calculate_campaign_duration(state),
                    "status": self._determine_campaign_status(state),
                    "overall_health": monitoring_results.get("pipeline_health", "unknown")
                },
                "pipeline_metrics": summary_stats,
                "conversion_funnel": conversion_rates,
                "sourcing_performance": {
                    "total_searched": sourcing_metrics.get("total_searched", 0),
                    "average_fit_score": sourcing_metrics.get("average_fit_score", 0),
                    "quality_score": sourcing_metrics.get("quality_score", 0),
                    "sources_used": sourcing_metrics.get("sources_used", [])
                },
                "outreach_performance": {
                    "response_rate": outreach_metrics.get("response_rate", 0),
                    "channels_used": outreach_metrics.get("channels_used", []),
                    "average_response_time": outreach_metrics.get("average_response_time", "N/A"),
                    "engagement_quality": outreach_metrics.get("engagement_quality", 0)
                },
                "candidate_details": self._generate_candidate_details(pipeline),
                "recommendations": self._generate_recommendations(state, summary_stats, conversion_rates),
                "next_steps": self._generate_next_steps(state, summary_stats)
            }
            
            # Update state with report
            state["final_report"] = report
            state["report_generated"] = True
            state["workflow_complete"] = True
            
            self.logger.info(f"✅ Report generated successfully: {report['report_id']}")
            
            # Log summary to console
            self._log_report_summary(report)
            
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Report generation failed: {e}")
            state["report_error"] = str(e)
            return state
    
    def _safe_percentage(self, numerator: int, denominator: int) -> float:
        """Safely calculate percentage, handling division by zero.
        
        Args:
            numerator: Numerator value
            denominator: Denominator value
            
        Returns:
            Percentage as float, 0.0 if denominator is zero
        """
        return (numerator / denominator * 100) if denominator > 0 else 0.0
    
    def _determine_campaign_status(self, state: RecruitmentExecutiveState) -> str:
        """Determine overall campaign status.
        
        Args:
            state: Current recruitment state
            
        Returns:
            Campaign status string
        """
        pipeline = state.get("candidate_pipeline", {})
        
        if pipeline.get("hired"):
            return "successful"
        elif pipeline.get("interviewed"):
            return "in_progress_interviews"
        elif pipeline.get("responded"):
            return "in_progress_outreach"
        elif pipeline.get("contacted"):
            return "awaiting_responses"
        elif pipeline.get("sourced"):
            return "sourcing_complete"
        else:
            return "initializing"
    
    def _generate_candidate_details(self, pipeline: Dict[str, List]) -> Dict[str, Any]:
        """Generate detailed candidate breakdown by pipeline stage.
        
        Args:
            pipeline: Candidate pipeline data
            
        Returns:
            Detailed candidate breakdown
        """
        details = {}
        
        for stage, candidates in pipeline.items():
            if candidates:
                details[stage] = {
                    "count": len(candidates),
                    "candidates": [
                        {
                            "name": candidate.get("name", "Unknown"),
                            "position": candidate.get("position", "N/A"),
                            "fit_score": candidate.get("fit_score", 0),
                            "source": candidate.get("source", "Unknown"),
                            "engagement_score": candidate.get("engagement_score", 0)
                        } for candidate in candidates[:5]  # Limit to top 5 per stage
                    ]
                }
        
        return details
    
    def _generate_recommendations(self, state: RecruitmentExecutiveState, summary_stats: Dict[str, int], conversion_rates: Dict[str, float]) -> List[str]:
        """Generate actionable recommendations based on campaign performance.
        
        Args:
            state: Current recruitment state
            summary_stats: Summary statistics
            conversion_rates: Conversion rate metrics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Sourcing recommendations
        if summary_stats["total_sourced"] < 5:
            recommendations.append("Increase sourcing efforts - target at least 10-15 candidates for better selection")
        
        # Outreach recommendations
        response_rate = conversion_rates["contacted_to_responded"]
        if response_rate < 10:
            recommendations.append("Improve outreach messaging - current response rate is below benchmark (10%)")
        elif response_rate > 30:
            recommendations.append("Excellent response rate! Consider scaling this outreach approach")
        
        # Conversion recommendations
        if conversion_rates["sourced_to_contacted"] < 50:
            recommendations.append("Review candidate qualification criteria - many sourced candidates are not being contacted")
        
        # Pipeline recommendations
        pipeline_health = state.get("monitoring_results", {}).get("pipeline_health", "unknown")
        if pipeline_health == "poor":
            recommendations.append("Pipeline health is poor - consider revising sourcing strategy or requirements")
        
        # Quality recommendations
        sourcing_metrics = state.get("sourcing_metrics", {})
        if sourcing_metrics.get("average_fit_score", 0) < 70:
            recommendations.append("Focus on higher quality candidates - average fit score is below target (70%)")
        
        if not recommendations:
            recommendations.append("Campaign is performing well - continue current approach")
        
        return recommendations
    
    def _generate_next_steps(self, state: RecruitmentExecutiveState, summary_stats: Dict[str, int]) -> List[str]:
        """Generate specific next steps based on current campaign state.
        
        Args:
            state: Current recruitment state
            summary_stats: Summary statistics
            
        Returns:
            List of next step strings
        """
        next_steps = []
        
        if summary_stats["total_hired"] > 0:
            next_steps.append("🎉 Recruitment successful! Begin onboarding process")
            next_steps.append("Document successful sourcing and outreach strategies for future campaigns")
        elif summary_stats["total_interviewed"] > 0:
            next_steps.append("📋 Follow up on interview results and make hiring decisions")
            next_steps.append("Prepare offer letters for successful candidates")
        elif summary_stats["total_responded"] > 0:
            next_steps.append("📞 Schedule interviews with responded candidates")
            next_steps.append("Prepare interview questions and evaluation criteria")
        elif summary_stats["total_contacted"] > 0:
            next_steps.append("⏳ Wait for candidate responses (allow 5-7 business days)")
            next_steps.append("Prepare follow-up messages for non-responders")
        elif summary_stats["total_sourced"] > 0:
            next_steps.append("📧 Initiate outreach campaign to sourced candidates")
            next_steps.append("Prepare personalized outreach messages")
        else:
            next_steps.append("🔍 Begin candidate sourcing for the position")
            next_steps.append("Define sourcing strategy and target channels")
        
        return next_steps
    
    def _log_report_summary(self, report: Dict[str, Any]) -> None:
        """Log a summary of the report to the console.
        
        Args:
            report: Generated report dictionary
        """
        summary = report["campaign_summary"]
        metrics = report["pipeline_metrics"]
        
        self.logger.info("📊 RECRUITMENT CAMPAIGN SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Position: {summary['position']}")
        self.logger.info(f"Status: {summary['status']}")
        self.logger.info(f"Duration: {summary['duration']}")
        self.logger.info(f"Health: {summary['overall_health']}")
        self.logger.info("")
        self.logger.info("📈 PIPELINE METRICS")
        self.logger.info(f"Sourced: {metrics['total_sourced']}")
        self.logger.info(f"Contacted: {metrics['total_contacted']}")
        self.logger.info(f"Responded: {metrics['total_responded']}")
        self.logger.info(f"Interviewed: {metrics['total_interviewed']}")
        self.logger.info(f"Hired: {metrics['total_hired']}")
        self.logger.info("=" * 50)
        """Generate final recruitment report."""
        logger.info(" Generating recruitment report...")
        
        pipeline = state.get("candidate_pipeline", {})
        strategy = state.get("recruitment_strategy", "unknown")
        
        report = {
            "recruitment_strategy": strategy,
            "candidates_sourced": len(pipeline.get("sourced", [])),
            "candidates_contacted": len(pipeline.get("contacted", [])),
            "candidates_responded": len(pipeline.get("responded", [])),
            "completion_time": datetime.now().isoformat(),
            "status": "completed"
        }
        
        # Add report to messages
        report_message = AIMessage(content=f"Recruitment process completed: {report}")
        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(report_message)
        
        state["next_action"] = "complete"
        
        logger.info(" Recruitment report generated")
        return state
    
    # ---- Conditional Logic ----
    
    def route_next_step(self, state: RecruitmentExecutiveState) -> str:
        """Determine the next step in the workflow."""
        next_action = state.get("next_action", "sourcing")
        
        if next_action == "sourcing":
            return "sourcing"
        elif next_action == "outreach":
            return "outreach"
        elif next_action == "monitor":
            return "monitor"
        else:
            return "complete"
    
    def should_continue_monitoring(self, state: RecruitmentExecutiveState) -> str:
        """Determine if monitoring should continue or complete."""
        next_action = state.get("next_action", "complete")
        
        if next_action == "continue":
            return "continue"
        else:
            return "complete"
    
    def run(self, user_request: str) -> Dict[str, Any]:
        """Run the complete recruitment workflow."""
        logger.info(f" Starting recruitment workflow for: {user_request}")
        
        # Initialize state
        initial_state = RecruitmentExecutiveState(
            messages=[HumanMessage(content=user_request)],
            user_request=None,
            current_projects=None,
            active_campaigns=None,
            candidate_pipeline={},
            recruitment_strategy="",
            next_action=""
        )
        
        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            
            logger.info("Recruitment workflow completed successfully")
            return {
                "success": True,
                "final_state": final_state,
                "candidate_pipeline": final_state.get("candidate_pipeline", {}),
                "strategy": final_state.get("recruitment_strategy", ""),
                "messages": [msg.content for msg in final_state.get("messages", [])]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "partial_state": {}
            }

# # Factory function for easy import
# def create_recruitment_flow(config: Dict[str, Any] = None) -> RecruitmentExecutiveFlow:
#     """Create and return a configured RecruitmentExecutiveFlow."""
#     return RecruitmentExecutiveFlow(config)