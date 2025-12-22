#!/usr/bin/env python3
"""
Main Entry Point - Recruitment Agent System (Backward Compatibility)

This file provides backward compatibility by importing from the new
Clean Architecture presentation layer.

For new code, use: from src.presentation.cli.main import RecruitmentSystem
"""

# Import from new Clean Architecture location
from src.presentation.cli.main import (
    RecruitmentSystem,
    setup_logging,
    create_parser,
    run_api_server,
    main,
    call_get_all_projects
)

# Re-export for backward compatibility
__all__ = [
    'RecruitmentSystem',
    'setup_logging',
    'create_parser',
    'run_api_server',
    'main',
    'call_get_all_projects'
]

# If run directly, execute the CLI
if __name__ == "__main__":
    import asyncio
    import sys
    from src.presentation.cli.main import create_parser
    
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == 'api':
        from src.presentation.cli.main import run_api_server, setup_logging, RecruitmentSystem
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
        try:
            exit_code = asyncio.run(main())
            sys.exit(exit_code)
        except KeyboardInterrupt:
            print("\n\n⚠️ System interrupted")
            sys.exit(1)
        except Exception as e:
            import logging
            logger = logging.getLogger('RecruitmentSystem')
            logger.error(f"Fatal error: {e}", exc_info=True)
            print(f"❌ Fatal error: {e}")
            sys.exit(1)
