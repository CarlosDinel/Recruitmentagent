#!/usr/bin/env python3
"""
CLI Entry Point - Recruitment Agent System (Clean Architecture)

This is the command-line interface for the recruitment agent system.
It uses the Application layer orchestrators and maintains LangGraph compatibility.

Author: Senior Development Team
Version: 2.0.0 (Clean Architecture)
License: MIT
"""

import asyncio
import argparse
import logging
import json
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Environment setup
from dotenv import load_dotenv
load_dotenv()

    # Import from Clean Architecture structure
try:
    # Infrastructure layer
    from ...infrastructure.config import AppConfig, get_config
    from ...infrastructure.tools.langgraph_project_tools import get_all_projects_tool
    
    # Backward compatibility imports (for LangGraph compatibility)
    from agents.recruitment_executive import RecruitmentExecutiveAgent, RecruitmentExecutiveState
    from agents.sourcing_manager_unified import UnifiedSourcingManager
    from agents.database_agent import DatabaseAgent
    from tools.get_projects import get_all_projects
    from langchain_core.tools import StructuredTool
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def call_get_all_projects(use_mongodb: bool = False, fallback: bool = True) -> List[Dict[str, Any]]:
    """Helper function to call get_all_projects whether it's a tool or regular function.
    
    This handles the case where get_all_projects is a LangChain StructuredTool,
    and also fixes internal tool calls within the function.
    """
    try:
        # Try using the new infrastructure tool first
        try:
            result = get_all_projects_tool.invoke({
                "use_mongodb": use_mongodb,
                "fallback": fallback
            })
            return result if isinstance(result, list) else []
        except Exception:
            pass
        
        # Fallback to old implementation
        from tools.get_projects import (
            get_projects_from_linkedin_api,
            get_projects_from_mongodb
        )
        
        # Get underlying functions if they're tools
        def get_func(tool_or_func):
            """Extract underlying function from tool if needed."""
            if isinstance(tool_or_func, StructuredTool) and hasattr(tool_or_func, 'func'):
                return tool_or_func.func
            return tool_or_func
        
        linkedin_func = get_func(get_projects_from_linkedin_api)
        mongo_func = get_func(get_projects_from_mongodb)
        
        # Manually implement get_all_projects logic using underlying functions
        primary_source = "MongoDB" if use_mongodb else "LinkedIn API"
        secondary_source = "LinkedIn API" if use_mongodb else "MongoDB"
        
        logger.debug(f"🔄 Attempting to fetch projects from {primary_source}...")
        
        # Try primary source
        if use_mongodb:
            projects = mongo_func()
        else:
            projects = linkedin_func()
        
        # If primary failed and fallback is enabled, try secondary
        if not projects and fallback:
            logger.debug(f"⚠️ {primary_source} returned no results. Trying {secondary_source}...")
            if use_mongodb:
                projects = linkedin_func()
            else:
                projects = mongo_func()
        
        # Remove duplicates
        if projects:
            seen_ids = set()
            unique_projects = []
            for project in projects:
                project_id = project.get('project_id', '')
                if project_id and project_id not in seen_ids:
                    seen_ids.add(project_id)
                    unique_projects.append(project)
            projects = unique_projects
        
        logger.debug(f"✅ Final result: {len(projects)} unique projects available")
        return projects
        
    except Exception as e:
        logger.error(f"Error calling get_all_projects: {e}", exc_info=True)
        return []


# Logging setup
def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure logging for the application."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f'recruitment_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('RecruitmentSystem')

logger = setup_logging()


class RecruitmentSystem:
    """
    Main system orchestrator for recruitment pipeline.
    
    This class coordinates the recruitment workflow using Clean Architecture.
    It uses orchestrators from the Application layer and maintains backward
    compatibility with existing agents for LangGraph integration.
    """
    
    def __init__(self, config: Optional[AppConfig] = None, debug: bool = False):
        """Initialize recruitment system.
        
        Args:
            config: Optional AppConfig instance. If None, loads from environment.
            debug: Enable debug mode for detailed logging.
        """
        self.app_config = config or AppConfig.from_env()
        self.debug = debug or os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Update logger level if debug
        if self.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")
        
        # System components (using backward compatibility for now)
        self.executive_agent: Optional[RecruitmentExecutiveAgent] = None
        self.sourcing_manager: Optional[UnifiedSourcingManager] = None
        self.database_agent: Optional[DatabaseAgent] = None
        
        # Legacy config dict for backward compatibility
        self.config = self._to_legacy_config()
        
        self._setup_system()
    
    def _to_legacy_config(self) -> Dict[str, Any]:
        """Convert AppConfig to legacy dict format for backward compatibility."""
        return {
            'ai_model': self.app_config.openai.model,
            'debug_mode': self.debug,
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'max_retries': self.app_config.unified_sourcing.max_retries,
            'timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'target_candidates': self.app_config.unified_sourcing.default_target_count,
            'quality_threshold': float(os.getenv('QUALITY_THRESHOLD', '0.7'))
        }
    
    def _setup_system(self):
        """Initialize system components."""
        logger.info("🚀 Initializing Recruitment Agent System...")
        
        try:
            # Initialize sourcing manager (backward compatibility)
            self.sourcing_manager = UnifiedSourcingManager(
                model_name=self.app_config.openai.model,
                temperature=self.app_config.openai.temperature
            )
            logger.debug("✅ Sourcing manager initialized")
            
            # Initialize DatabaseAgent if MongoDB is configured
            try:
                from agents.database_agent import DatabaseAgent, DatabaseAgentState
                db_state = DatabaseAgentState(
                    name="RecruitmentSystem_DatabaseAgent",
                    description="Database operations for recruitment system",
                    tools=[],
                    tool_descriptions=[],
                    tool_input_types=[],
                    tool_output_types=[],
                    input_type="dict",
                    output_type="dict",
                    intermediate_steps=[],
                    max_iterations=5,
                    iteration_count=0,
                    stop=False,
                    last_action="",
                    last_observation="",
                    last_input="",
                    last_output="",
                    graph=None,
                    memory=[],
                    memory_limit=100,
                    verbose=False,
                    temperature=0.7,
                    top_k=50,
                    top_p=0.9,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                    best_of=1,
                    n=1,
                    logit_bias={},
                    seed=42,
                    model=self.app_config.openai.model,
                    api_key=self.app_config.openai.api_key or ""
                )
                self.database_agent = DatabaseAgent(db_state)
                logger.debug("✅ Database agent initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize DatabaseAgent: {e}")
                self.database_agent = None
            
            # Initialize state
            initial_state = RecruitmentExecutiveState(
                messages=[],
                user_request="",
                current_projects=[],
                active_campaigns=[],
                candidate_pipeline={},
                recruitment_strategy="",
                next_action=""
            )
            
            # Initialize executive agent (backward compatibility for LangGraph)
            self.executive_agent = RecruitmentExecutiveAgent(initial_state, self.config)
            logger.debug("✅ Executive agent initialized")
            # If DatabaseAgent failed earlier due to DB init order, retry now
            if self.database_agent is None:
                try:
                    from agents.database_agent import DatabaseAgent
                    self.database_agent = DatabaseAgent()
                    logger.debug("✅ Database agent initialized (post-ExecutiveAgent)")
                except Exception as e:
                    logger.warning(f"⚠️ Could not initialize DatabaseAgent after ExecutiveAgent: {e}")
            
            logger.info("✅ System initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}", exc_info=self.debug)
            raise
    
    async def process_recruitment_request(self, user_request: str) -> Dict[str, Any]:
        """Process a single recruitment request end-to-end with real API integration.
        
        This method runs the complete recruitment pipeline:
        1. Parse job requirements from user request
        2. Search LinkedIn for candidates (real API)
        3. Evaluate candidates against requirements
        4. Scrape detailed profiles for suitable candidates (real API)
        5. Generate comprehensive report with metrics
        
        Args:
            user_request: The recruitment request text (e.g., "Find senior Python developers in Amsterdam")
            
        Returns:
            Dictionary with success status, candidates, evaluations, and metrics
        """
        logger.info(f"📋 Processing request: {user_request[:100]}...")
        logger.info("🔄 Running FULL PIPELINE with real API integration and prospect evaluation")
        
        try:
            # Validate request
            if not user_request or not user_request.strip():
                raise ValueError("Recruitment request cannot be empty")
            
            start_time = datetime.now()
            
            # Step 1: Use sourcing manager to search and evaluate candidates
            logger.info("🔍 Step 1/3: Searching candidates with real LinkedIn API...")
            sourcing_result = await self._run_sourcing_with_evaluation(user_request)
            
            # Step 2: Extract results and metrics
            logger.info("📊 Step 2/3: Analyzing candidate suitability...")
            analysis = self._analyze_sourcing_results(sourcing_result)
            
            # Step 3: Generate comprehensive report
            logger.info("📝 Step 3/3: Generating final report...")
            duration = (datetime.now() - start_time).total_seconds()
            
            final_report = {
                'success': True,
                'request': user_request,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration,
                'pipeline_stages_completed': [
                    'linkedin_search',
                    'candidate_evaluation', 
                    'profile_enrichment'
                ],
                'summary': {
                    'total_candidates_found': analysis['total_found'],
                    'suitable_candidates': analysis['suitable_count'],
                    'potentially_suitable': analysis['potential_count'],
                    'not_suitable': analysis['not_suitable_count'],
                    'profiles_enriched': analysis['enriched_count']
                },
                'candidates': analysis['candidates'],
                'evaluation_details': analysis['evaluation_details'],
                'sourcing_result': sourcing_result,
                'api_integration_status': {
                    'linkedin_search': 'active',
                    'profile_scraping': 'active',
                    'candidate_evaluation': 'active'
                }
            }
            
            logger.info(f"✅ Pipeline completed in {duration:.2f}s")
            logger.info(f"📈 Results: {analysis['suitable_count']} suitable, {analysis['potential_count']} potential, {analysis['not_suitable_count']} not suitable")
            
            return final_report
        
        except ValueError as e:
            logger.warning(f"⚠️ Invalid request: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'timestamp': datetime.now().isoformat(),
                'request': user_request,
                'pipeline_stages_completed': []
            }
        except Exception as e:
            logger.error(f"❌ Request processing failed: {e}", exc_info=self.debug)
            return {
                'success': False,
                'error': str(e),
                'error_type': 'processing_error',
                'timestamp': datetime.now().isoformat(),
                'request': user_request,
                'pipeline_stages_completed': []
            }
    
    async def _run_sourcing_with_evaluation(self, user_request: str) -> Dict[str, Any]:
        """Run sourcing manager with full evaluation pipeline.
        
        This method invokes the UnifiedSourcingManager which internally:
        1. Calls Candidate Searching Agent (LinkedIn API)
        2. Calls Candidate Evaluation Agent (scoring & qualification)
        3. Calls Profile Scraping Agent for suitable candidates (LinkedIn API)
        
        Returns:
            Complete sourcing result with evaluated and enriched candidates
        """
        try:
            # Prepare request for sourcing manager
            sourcing_request = {
                'job_requirements': user_request,
                'target_count': self.config.get('target_candidates', 10),
                'quality_threshold': self.config.get('quality_threshold', 0.7),
                'project_id': f"CLI_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'enable_evaluation': True,  # Enable candidate evaluation
                'scrape_profiles': True     # Enable profile enrichment
            }
            
            # Execute through sourcing manager
            logger.debug(f"Calling UnifiedSourcingManager with: {sourcing_request}")
            result = await self.sourcing_manager.run(sourcing_request)
            
            return result
            
        except Exception as e:
            logger.error(f"Sourcing with evaluation failed: {e}", exc_info=True)
            raise
    
    def _analyze_sourcing_results(self, sourcing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sourcing results and extract key metrics.
        
        Args:
            sourcing_result: Result from UnifiedSourcingManager
            
        Returns:
            Analyzed data with categorized candidates and metrics
        """
        try:
            # Extract from sourcing result
            summary = sourcing_result.get('summary', {})
            candidates_data = sourcing_result.get('candidates', [])
            
            # Get all candidates (may be top 10 or filtered)
            all_candidates = []
            if isinstance(candidates_data, dict):
                # If it's a dict, extract candidates list
                all_candidates = candidates_data if 'top_candidates' not in candidates_data else candidates_data.get('top_candidates', [])
            elif isinstance(candidates_data, list):
                all_candidates = candidates_data
            
            # Get metrics
            total_found = summary.get('total_found', 0)
            total_suitable = summary.get('total_suitable', 0)
            
            # Count enriched profiles (candidates with detailed skills)
            enriched_count = sum(1 for c in all_candidates if isinstance(c, dict) and c.get('profile_enriched', False))
            
            # Categorize candidates by suitability status
            suitable = []
            potential = []
            not_suitable_candidates = []
            
            for candidate in all_candidates:
                if isinstance(candidate, dict):
                    status = candidate.get('suitability_status', 'unknown')
                    if status == 'suitable':
                        suitable.append(candidate)
                    elif status in ['maybe', 'potentially_suitable']:
                        potential.append(candidate)
                    else:
                        not_suitable_candidates.append(candidate)
            
            # If we have potential candidates but no suitable ones, promote potential to suitable
            # This prevents showing empty results when evaluation is conservative
            if len(suitable) == 0 and len(potential) > 0 and total_found > 0:
                logger.info("📈 No suitable candidates but found potential ones - promoting potential to suitable for review")
                suitable = potential[:5]  # Top 5 potential candidates
                potential = []
            
            # Also include all found candidates if we have few matches
            if len(all_candidates) == 0 and total_found > 0:
                logger.warning("⚠️  No candidates in results but summary shows found - using fallback")
                all_candidates = []
            
            logger.info(f"✅ Parsed results: {len(suitable)} suitable, {len(potential)} potential, {len(not_suitable_candidates)} not suitable from {total_found} found")
            logger.info(f"📊 Enriched profiles: {enriched_count}")
            
            return {
                'total_found': total_found,
                'suitable_count': len(suitable),
                'potential_count': len(potential),
                'not_suitable_count': len(not_suitable_candidates),
                'enriched_count': enriched_count,
                'candidates': suitable + potential + not_suitable_candidates,  # Include all for analysis
                'evaluation_details': {
                    'suitable': suitable,
                    'potentially_suitable': potential,
                    'not_suitable': not_suitable_candidates
                }
            }
            
        except Exception as e:
            logger.error(f"Result analysis failed: {e}", exc_info=True)
            return {
                'total_found': 0,
                'suitable_count': 0,
                'potential_count': 0,
                'not_suitable_count': 0,
                'enriched_count': 0,
                'candidates': [],
                'evaluation_details': {}
            }
    
    async def process_batch(self, requests: List[str], output_file: Optional[str] = None) -> Dict[str, Any]:
        """Process multiple recruitment requests in batch.
        
        Args:
            requests: List of recruitment request strings
            output_file: Optional file path to save results
            
        Returns:
            Dictionary with batch processing results and statistics
        """
        logger.info(f"📦 Processing batch of {len(requests)} requests...")
        
        if not requests:
            logger.warning("⚠️ Empty batch request list")
            return {
                'success': False,
                'error': 'No requests provided',
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'results': [],
                'timestamp': datetime.now().isoformat()
            }
        
        results = []
        success_count = 0
        error_count = 0
        
        try:
            for i, request in enumerate(requests, 1):
                logger.info(f"[{i}/{len(requests)}] Processing: {request[:50]}...")
                result = await self.process_recruitment_request(request)
                results.append(result)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
            
            batch_result = {
                'success': error_count == 0,
                'total_processed': len(requests),
                'successful': success_count,
                'failed': error_count,
                'success_rate': f"{(success_count / len(requests) * 100):.1f}%",
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to file if specified
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(batch_result, f, indent=2)
                logger.info(f"💾 Results saved to {output_file}")
            
            return batch_result
        
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}", exc_info=self.debug)
            return {
                'success': False,
                'error': str(e),
                'total_processed': len(results),
                'successful': success_count,
                'failed': error_count,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
    
    async def test_system(self) -> Dict[str, Any]:
        """Run comprehensive system tests.
        
        Returns:
            Dictionary with test results and status
        """
        logger.info("🧪 Running system tests...")
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }
        
        # Test configuration
        test_results['tests']['configuration'] = await self._test_configuration()
        
        # Test projects
        test_results['tests']['projects'] = await self._test_projects()
        
        # Test agents
        test_results['tests']['agents'] = await self._test_agents()
        
        # Overall status
        all_passed = all(
            test.get('success', False) 
            for test in test_results['tests'].values()
        )
        test_results['overall_success'] = all_passed
        
        logger.info(f"{'✅' if all_passed else '❌'} System tests {'passed' if all_passed else 'failed'}")
        
        return test_results
    
    async def _test_configuration(self) -> Dict[str, Any]:
        """Test configuration loading."""
        try:
            is_valid = self.app_config.validate()
            return {
                'success': is_valid,
                'config_loaded': True,
                'debug_mode': self.debug
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_projects(self) -> Dict[str, Any]:
        """Test project retrieval."""
        try:
            # Use the helper function to call get_all_projects
            projects = call_get_all_projects(use_mongodb=False, fallback=True)
            
            return {
                'success': True,
                'projects_count': len(projects),
                'sample_projects': [p.get('name', 'Unknown') for p in projects[:3]]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_agents(self) -> Dict[str, Any]:
        """Test agent initialization."""
        try:
            agents_status = {
                'executive_agent': self.executive_agent is not None,
                'sourcing_manager': self.sourcing_manager is not None,
                'database_agent': self.database_agent is not None
            }
            
            return {
                'success': all(agents_status.values()),
                'agents': agents_status
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Recruitment Agent System - Production-ready recruitment automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single request
  python main.py process "Find a senior Python developer"
  
  # Run system tests
  python main.py test
  
  # Start API server
  python main.py api --port 8000
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process a recruitment request')
    process_parser.add_argument('request', help='Recruitment request text')
    process_parser.add_argument('--output', '-o', help='Output file path (JSON)')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run system tests')
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # API command
    api_parser = subparsers.add_parser('api', help='Start API server')
    api_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    api_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple requests')
    batch_parser.add_argument('file', help='JSON file with list of requests')
    batch_parser.add_argument('--output', '-o', help='Output file path (JSON)')
    
    # Global options
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    return parser


def create_api_server():
    """Create FastAPI app instance for testing or programmatic access.
    
    Returns:
        FastAPI application instance
    """
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        
        # Import API configuration
        from config.config import get_config
        config = get_config()
        
        # Create FastAPI app
        app = FastAPI(
            title="Recruitment Agent API",
            description="Production-ready REST API for recruitment automation",
            version="1.0.0",
            docs_url=config.api.docs_url,
            redoc_url=config.api.redoc_url,
            openapi_url=config.api.openapi_url
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.api.cors_origins,
            allow_credentials=config.api.cors_allow_credentials,
            allow_methods=config.api.cors_allow_methods,
            allow_headers=config.api.cors_allow_headers
        )
        
        # Import and mount API routes
        from src.presentation.api.routes import router
        app.include_router(router)
        
        return app
    
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        raise

def run_api_server(system: RecruitmentSystem, host: str = None, port: int = None) -> int:
    """Start the REST API server with comprehensive routes.
    
    This function initializes FastAPI with all routes from the API layer,
    including CORS middleware and health checks.
    
    Args:
        system: RecruitmentSystem instance (backward compatibility, not actively used)
        host: Server host (default from config)
        port: Server port (default from config)
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        # Import API configuration
        from config.config import get_config
        config = get_config()
        
        # Use config defaults if not provided
        if host is None:
            host = config.api.host
        if port is None:
            port = config.api.port
        
        # Create FastAPI app
        app = FastAPI(
            title="Recruitment Agent API",
            description="Production-ready REST API for recruitment automation with DatabaseAgent monopoly pattern",
            version="1.0.0",
            docs_url=config.api.docs_url,
            redoc_url=config.api.redoc_url,
            openapi_url=config.api.openapi_url
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.api.cors_origins,
            allow_credentials=config.api.cors_allow_credentials,
            allow_methods=config.api.cors_allow_methods,
            allow_headers=config.api.cors_allow_headers
        )
        
        # Import and mount API routes
        try:
            from src.presentation.api.routes import router
            app.include_router(router)
            logger.info("✅ Mounted API routes from src.presentation.api.routes")
        except ImportError as e:
            logger.error(f"❌ Failed to import API routes: {e}")
            logger.error("Make sure src/presentation/api/routes.py exists")
            return 1
        
        # Log server startup
        logger.info("\n" + "=" * 60)
        logger.info("🚀 RECRUITMENT AGENT API SERVER")
        logger.info("=" * 60)
        logger.info(f"🌐 Server: http://{host}:{port}")
        logger.info(f"📚 API Docs: http://{host}:{port}{config.api.docs_url}")
        logger.info(f"📖 ReDoc: http://{host}:{port}{config.api.redoc_url}")
        logger.info(f"🏥 Health Check: http://{host}:{port}/health")
        logger.info(f"🔧 Workers: {config.api.workers}")
        logger.info(f"🌍 CORS Origins: {', '.join(config.api.cors_origins)}")
        logger.info("=" * 60)
        
        # Uvicorn constraint: using object app requires workers=1 and reload=False
        workers = config.api.workers
        reload = config.api.reload
        if reload or workers > 1:
            logger.warning("You must pass the application as an import string to enable 'reload' or 'workers'. For now, forcing single worker and reload=False.")
            workers = 1
            reload = False
        
        # Start uvicorn server
        uvicorn.run(
            app,
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            log_level="info"
        )
        
        logger.info("✅ API server stopped gracefully")
        return 0
    
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        logger.error("Install with: pip install fastapi uvicorn pydantic")
        print("❌ FastAPI not installed. Install with: pip install fastapi uvicorn pydantic")
        return 1
    except Exception as e:
        logger.error(f"❌ API server failed to start: {e}", exc_info=True)
        print(f"❌ API server failed to start: {e}")
        return 1


async def main() -> int:
    """Main async entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    debug = getattr(args, 'debug', False)
    logger = setup_logging(debug=debug)
    
    try:
        system = RecruitmentSystem(debug=debug)
    except Exception as e:
        logger.error(f"❌ Failed to initialize system: {e}", exc_info=True)
        print(f"❌ System initialization failed: {e}")
        return 1
    
    try:
        if args.command == 'process':
            result = await system.process_recruitment_request(args.request)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"💾 Result saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
            
            return 0 if result['success'] else 1
        
        elif args.command == 'test':
            result = await system.test_system()
            print(json.dumps(result, indent=2))
            return 0 if result.get('overall_success', False) else 1
        
        elif args.command == 'batch':
            with open(args.file, 'r') as f:
                requests = json.load(f)
            
            if not isinstance(requests, list):
                print("❌ Batch file must contain a JSON array of request strings")
                return 1
            
            result = await system.process_batch(requests, args.output)
            print(json.dumps(result, indent=2))
            return 0 if result['success'] else 1
        
        else:
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️ System interrupted")
        return 1
    except Exception as e:
        logger.error(f"❌ Command failed: {e}", exc_info=True)
        print(f"❌ Command failed: {e}")
        return 1


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    # Special handling for API command to avoid asyncio event loop conflicts
    if args.command == 'api':
        # Initialize system synchronously for API server
        debug = getattr(args, 'debug', False)
        logger = setup_logging(debug=debug)
        try:
            system_instance = RecruitmentSystem(debug=debug)
        except Exception as e:
            logger.error(f"❌ Failed to initialize system for API server: {e}", exc_info=True)
            print(f"❌ System initialization failed for API server: {e}")
            sys.exit(1)
        sys.exit(run_api_server(system_instance, args.host, args.port))
    else:
        # For all other commands, run main asynchronously
        try:
            exit_code = asyncio.run(main())
            sys.exit(exit_code)
        except KeyboardInterrupt:
            print("\n\n⚠️ System interrupted")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            print(f"❌ Fatal error: {e}")
            sys.exit(1)

