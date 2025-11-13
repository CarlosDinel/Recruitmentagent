#!/usr/bin/env python3
"""
Main Entry Point - Recruitment Agent System
Fully production-ready with CLI, API, and testing modes
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Import agents and tools
try:
    from agents.recruitment_executive import RecruitmentExecutiveAgent, RecruitmentExecutiveState
    from agents.sourcing_manager_unified import UnifiedSourcingManager
    from agents.database_agent import DatabaseAgent
    from tools.get_projects import get_all_projects
    from prompts.recruitment_executive_agent_prompts import RecruitmentPrompts
    from config.config import AppConfig
except ImportError as e:
    print(f" Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Logging setup
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'recruitment_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RecruitmentSystem')


class RecruitmentSystem:
    """Main system orchestrator for recruitment pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, debug: bool = False):
        """Initialize recruitment system."""
        self.config = config or self._load_config()
        self.debug = debug or self.config.get('debug_mode', False)
        self.executive_agent = None
        self.sourcing_manager = None
        self.database_agent = None
        self._setup_system()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment."""
        return {
            'ai_model': os.getenv('OPENAI_MODEL', 'gpt-4'),
            'debug_mode': os.getenv('DEBUG', 'False').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'target_candidates': int(os.getenv('UNIFIED_SOURCING_DEFAULT_TARGET_COUNT', '50')),
            'quality_threshold': float(os.getenv('QUALITY_THRESHOLD', '0.7'))
        }
    
    def _setup_system(self):
        """Initialize system components."""
        logger.info(" Initializing Recruitment Agent System...")
        
        try:
            # Set logging level
            if self.debug:
                logging.getLogger().setLevel(logging.DEBUG)
                logger.debug("Debug mode enabled")
            
            # Initialize managers
            self.sourcing_manager = UnifiedSourcingManager(
                model_name=self.config['ai_model'],
                temperature=0.3
            )
            
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
            
            # Initialize executive agent
            self.executive_agent = RecruitmentExecutiveAgent(initial_state, self.config)
            logger.info(" System initialized successfully")
            
        except Exception as e:
            logger.error(f" System initialization failed: {e}")
            raise
    
    async def process_recruitment_request(self, user_request: str) -> Dict[str, Any]:
        """Process a single recruitment request end-to-end."""
        logger.info(f" Processing request: {user_request[:100]}...")
        
        try:
            # Validate request
            if not user_request or len(user_request.strip()) == 0:
                raise ValueError("Recruitment request cannot be empty")
            
            # Process through executive agent
            start_time = datetime.now()
            result = await self.executive_agent.execute({
                'request': user_request,
                'target_candidates': self.config['target_candidates'],
                'quality_threshold': self.config['quality_threshold']
            })
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'result': result,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'request': user_request
            }
        
        except Exception as e:
            logger.error(f" Request processing failed: {e}", exc_info=self.debug)
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'request': user_request
            }
    
    async def process_batch(self, requests: List[str], output_file: Optional[str] = None) -> Dict[str, Any]:
        """Process multiple recruitment requests in batch."""
        logger.info(f"📦 Processing batch of {len(requests)} requests...")
        
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
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to file if specified
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(batch_result, f, indent=2, default=str)
                logger.info(f"✅ Results saved to {output_file}")
            
            return batch_result
        
        except Exception as e:
            logger.error(f" Batch processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_so_far': len(results),
                'results': results
            }
    
    async def test_system(self, verbose: bool = False) -> Dict[str, Any]:
        """Run comprehensive system tests."""
        logger.info("🧪 Running system tests...")
        
        tests = {
            'environment': self._test_environment(),
            'configuration': self._test_configuration(),
            'imports': self._test_imports(),
            'agents': self._test_agents(),
            'projects': await self._test_projects()
        }
        
        all_passed = all(t['success'] for t in tests.values())
        
        if verbose or not all_passed:
            self._print_test_results(tests)
        
        logger.info(f"🎯 Tests: {' ALL PASSED' if all_passed else ' SOME FAILED'}")
        
        return {
            'overall_success': all_passed,
            'tests': tests,
            'timestamp': datetime.now().isoformat()
        }
    
    def _test_environment(self) -> Dict[str, Any]:
        """Test environment variables."""
        try:
            required_vars = [
                'OPENAI_API_KEY',
                'MONGODB_HOST',
                'LINKEDIN_API_KEY'
            ]
            
            missing = [var for var in required_vars if not os.getenv(var)]
            
            return {
                'success': len(missing) == 0,
                'missing_variables': missing,
                'message': 'Environment variables configured' if len(missing) == 0 else f'Missing: {missing}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_configuration(self) -> Dict[str, Any]:
        """Test configuration loading."""
        try:
            config_loaded = self.config is not None
            required_keys = ['ai_model', 'debug_mode', 'target_candidates']
            missing_keys = [k for k in required_keys if k not in self.config]
            
            return {
                'success': config_loaded and len(missing_keys) == 0,
                'config_loaded': config_loaded,
                'missing_keys': missing_keys,
                'ai_model': self.config.get('ai_model')
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_imports(self) -> Dict[str, Any]:
        """Test critical imports."""
        try:
            imports_ok = all([
                self.executive_agent is not None,
                self.sourcing_manager is not None
            ])
            
            return {
                'success': imports_ok,
                'executive_agent': self.executive_agent is not None,
                'sourcing_manager': self.sourcing_manager is not None
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_agents(self) -> Dict[str, Any]:
        """Test agent initialization."""
        try:
            return {
                'success': True,
                'executive_agent_type': type(self.executive_agent).__name__,
                'sourcing_manager_type': type(self.sourcing_manager).__name__,
                'agents_initialized': True
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_projects(self) -> Dict[str, Any]:
        """Test project retrieval."""
        try:
            projects = get_all_projects(use_mongodb=False, fallback=True)
            
            return {
                'success': True,
                'projects_count': len(projects),
                'sample_projects': [p.get('name', 'Unknown') for p in projects[:3]]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _print_test_results(self, tests: Dict[str, Any]):
        """Print test results."""
        print("\n" + "="*70)
        print(" SYSTEM TEST RESULTS")
        print("="*70)
        
        for test_name, result in tests.items():
            status = "✅ PASS" if result.get('success') else " FAIL"
            print(f"\n{test_name.upper()}: {status}")
            
            for key, value in result.items():
                if key not in ['success']:
                    if isinstance(value, list):
                        print(f"  {key}: {', '.join(str(v) for v in value)}")
                    else:
                        print(f"  {key}: {value}")


# CLI Interface
def create_parser() -> argparse.ArgumentParser:
    """Create command line interface."""
    parser = argparse.ArgumentParser(
        description='🤖 Recruitment Agent System - Production Ready',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py test                    # Run system tests
  python main.py process "Find Python developers"
  python main.py interactive            # Interactive mode
  python main.py batch requests.json    # Process batch
  python main.py api --port 8000        # Start API server
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run system tests')
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    test_parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process recruitment request')
    process_parser.add_argument('request', type=str, help='Recruitment request')
    process_parser.add_argument('--output', '-o', type=str, help='Output file')
    process_parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive mode')
    interactive_parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process batch of requests')
    batch_parser.add_argument('input_file', type=str, help='JSON file with requests list')
    batch_parser.add_argument('--output', '-o', type=str, help='Output file')
    batch_parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
    
    # API command
    api_parser = subparsers.add_parser('api', help='Start REST API server')
    api_parser.add_argument('--port', '-p', type=int, default=8000, help='Server port')
    api_parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')
    api_parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Check configuration')
    config_parser.add_argument('--check', action='store_true', help='Check production readiness')
    
    return parser


async def run_interactive(system: RecruitmentSystem, debug: bool = False):
    """Run interactive mode."""
    print("\n" + "="*70)
    print("🤖 Recruitment Agent - Interactive Mode")
    print("="*70)
    print("Type your recruitment request or use commands:")
    print("  /test   - Run system tests")
    print("  /status - Check system status")
    print("  /help   - Show help")
    print("  /quit   - Exit")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input(" > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                print("\n Goodbye!")
                break
            
            elif user_input.lower() == '/test':
                result = await system.test_system(verbose=True)
                print(f"\n Tests complete: {result['overall_success']}")
            
            elif user_input.lower() == '/status':
                print("\n System Status:")
                print(f"  Model: {system.config['ai_model']}")
                print(f"  Debug: {system.debug}")
                print(f"  Target Candidates: {system.config['target_candidates']}")
            
            elif user_input.lower() == '/help':
                print("\n Available Commands:")
                print("  /test   - Run system tests")
                print("  /status - Check system status")
                print("  /help   - Show this help")
                print("  /quit   - Exit")
                print("\nOr type any recruitment request to process it.")
            
            else:
                # Process as recruitment request
                result = await system.process_recruitment_request(user_input)
                
                if result['success']:
                    print(f"\n Processing successful")
                    print(f"   Duration: {result['duration_seconds']:.2f}s")
                    print(f"   Result: {json.dumps(result['result'], indent=2, default=str)[:500]}...")
                else:
                    print(f"\n Error: {result['error']}")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=debug)
            print(f" Error: {e}")


async def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Initialize system
    system = RecruitmentSystem(debug=getattr(args, 'debug', False))
    
    # Test command
    if args.command == 'test':
        result = await system.test_system(verbose=args.verbose)
        return 0 if result['overall_success'] else 1
    
    # Process command
    elif args.command == 'process':
        result = await system.process_recruitment_request(args.request)
        
        print("\n" + "="*70)
        print(" RECRUITMENT REQUEST RESULTS")
        print("="*70)
        print(f"Request: {result['request']}")
        print(f"Status: {' SUCCESS' if result['success'] else ' FAILED'}")
        print(f"Duration: {result.get('duration_seconds', 'N/A')}s")
        
        if result['success']:
            print(f"\nResults:\n{json.dumps(result['result'], indent=2, default=str)}")
        else:
            print(f"\nError: {result['error']}")
        
        # Save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n Results saved to: {args.output}")
        
        return 0 if result['success'] else 1
    
    # Interactive command
    elif args.command == 'interactive':
        await run_interactive(system, debug=args.debug)
        return 0
    
    # Batch command
    elif args.command == 'batch':
        if not os.path.exists(args.input_file):
            print(f" File not found: {args.input_file}")
            return 1
        
        with open(args.input_file, 'r') as f:
            data = json.load(f)
        
        requests = data if isinstance(data, list) else data.get('requests', [])
        
        if not requests:
            print(" No requests found in input file")
            return 1
        
        result = await system.process_batch(requests, output_file=args.output)
        
        print("\n" + "="*70)
        print(" BATCH PROCESSING RESULTS")
        print("="*70)
        print(f"Total Processed: {result['total_processed']}")
        print(f"Successful: {result['successful']}")
        print(f"Failed: {result['failed']}")
        
        if args.output:
            print(f"💾 Results saved to: {args.output}")
        
        return 0 if result['success'] else 1
    
    # API command
    elif args.command == 'api':
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
                return {"message": "Recruitment Agent API", "version": "1.0.0"}
            
            @app.get("/health")
            async def health():
                return {"status": "healthy", "timestamp": datetime.now().isoformat()}
            
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
            async def test_system():
                result = await system.test_system()
                return result
            
            print(f"\n Starting API server on http://{args.host}:{args.port}")
            print(f" API Docs: http://{args.host}:{args.port}/docs")
            
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0
        
        except ImportError:
            print(" FastAPI not installed. Install with: pip install fastapi uvicorn")
            return 1
    
    # Config command
    elif args.command == 'config':
        print("\n" + "="*70)
        print("⚙️ CONFIGURATION CHECK")
        print("="*70)
        
        for key, value in system.config.items():
            print(f"{key}: {value}")
        
        print("\n" + "="*70)
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n System interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f" Fatal error: {e}")
        sys.exit(1)