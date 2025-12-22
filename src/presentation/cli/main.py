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
    from prompts.recruitment_executive_agent_prompts import RecruitmentPrompts
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
            
            logger.info("✅ System initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}", exc_info=self.debug)
            raise
    
    async def process_recruitment_request(self, user_request: str) -> Dict[str, Any]:
        """Process a single recruitment request end-to-end.
        
        Args:
            user_request: The recruitment request text
            
        Returns:
            Dictionary with success status, result, and metadata
        """
        logger.info(f"📋 Processing request: {user_request[:100]}...")
        
        try:
            # Validate request
            if not user_request or not user_request.strip():
                raise ValueError("Recruitment request cannot be empty")
            
            # Process through executive agent
            start_time = datetime.now()
            result = await self.executive_agent.execute({
                'request': user_request,
                'target_candidates': self.config['target_candidates'],
                'quality_threshold': self.config['quality_threshold']
            })
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Request processed successfully in {duration:.2f}s")
            
            return {
                'success': True,
                'result': result,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'request': user_request
            }
        
        except ValueError as e:
            logger.warning(f"⚠️ Invalid request: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'timestamp': datetime.now().isoformat(),
                'request': user_request
            }
        except Exception as e:
            logger.error(f"❌ Request processing failed: {e}", exc_info=self.debug)
            return {
                'success': False,
                'error': str(e),
                'error_type': 'processing_error',
                'timestamp': datetime.now().isoformat(),
                'request': user_request
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


def run_api_server(system: RecruitmentSystem, host: str = '0.0.0.0', port: int = 8000) -> int:
    """Start the REST API server.
    
    This function is synchronous to avoid event loop conflicts with uvicorn.run()
    """
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import JSONResponse
        import uvicorn
        
        app = FastAPI(
            title="Recruitment Agent API",
            description="Production-ready recruitment automation",
            version="1.0.0"
        )
        
        @app.get("/")
        async def root():
            return {
                "message": "Recruitment Agent API",
                "version": "1.0.0",
                "status": "operational"
            }
        
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "ai_model": system.app_config.openai.model,
                    "debug_mode": system.debug
                }
            }
        
        @app.post("/process")
        async def process_request(request: Dict[str, str]):
            if 'request' not in request:
                raise HTTPException(status_code=400, detail="Missing 'request' field")
            
            result = await system.process_recruitment_request(request['request'])
            return result
        
        @app.post("/batch")
        async def process_batch(data: Dict[str, list]):
            if 'requests' not in data:
                raise HTTPException(status_code=400, detail="Missing 'requests' field")
            
            result = await system.process_batch(data['requests'])
            return result
        
        @app.get("/test")
        async def test_system_api():
            result = await system.test_system()
            return result
        
        logger.info(f"\n🚀 Starting API server on http://{host}:{port}")
        logger.info(f"📚 API Docs: http://{host}:{port}/docs")
        logger.info(f"🏥 Health Check: http://{host}:{port}/health")
        
        uvicorn.run(app, host=host, port=port, log_level="info")
        logger.info("✅ API server started successfully!")
        return 0
    
    except ImportError:
        logger.error("❌ FastAPI not installed. Install with: pip install fastapi uvicorn")
        print("❌ FastAPI not installed. Install with: pip install fastapi uvicorn")
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

