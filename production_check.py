"""
Quick Configuration Checker for Production Deployment

This script checks your .env configuration and provides a production readiness checklist.
"""

import sys
import os
sys.path.append('/Users/carlosalmeida/development/Recruitment-agent')

from config.config import get_config, validate_config, print_config_summary

def check_production_readiness():
    """Check if the system is ready for production deployment"""
    
    print("🔍 PRODUCTION READINESS CHECK")
    print("=" * 60)
    
    config = get_config()
    
    # Critical checks
    critical_issues = []
    warnings = []
    
    # 1. OpenAI API Key
    if not config.openai.api_key or config.openai.api_key == "your_openai_api_key_here":
        critical_issues.append("OpenAI API key not configured - AI decisions will not work")
    else:
        print(" OpenAI API key configured")
    
    # 2. LinkedIn API  
    if not config.linkedin.api_key:
        critical_issues.append("LinkedIn API key missing - candidate search will fail")
    else:
        print(" LinkedIn API key configured")
    
    if config.linkedin.account_id == "your_linkedin_account_id_here":
        warnings.append("
         LinkedIn account ID not updated from placeholder")
    else:
        print(" LinkedIn account ID configured")
    
    # 3. MongoDB
    if not all([config.mongodb.username, config.mongodb.password, config.mongodb.host]):
        critical_issues.append("
         MongoDB credentials incomplete - database storage will fail")
    else:
        print(" MongoDB credentials configured")
    
    # 4. Debug mode
    if config.debug:
        warnings.append("
         DEBUG mode still enabled - consider setting DEBUG=False for production")
    else:
        print(" Production mode enabled (DEBUG=False)")
    
    # 5. Component enablement
    if not config.unified_sourcing.enabled:
        warnings.append("
         Unified Sourcing Manager is disabled")
    else:
        print(" Unified Sourcing Manager enabled")
    
    if not config.database_agent.enabled:
        critical_issues.append("
         Database Agent disabled - candidate storage will fail")
    else:
        print(" Database Agent enabled")
    
    if not config.database_agent.linkedin_url_unique_key:
        warnings.append("
         LinkedIn URL unique key disabled - may cause duplicates")
    else:
        print(" LinkedIn URL unique key enabled")
    
    # 6. Pipeline components
    pipeline_issues = []
    if not config.candidate_pipeline.search_enabled:
        pipeline_issues.append("Candidate Search disabled")
    if not config.candidate_pipeline.evaluation_enabled:
        pipeline_issues.append("Candidate Evaluation disabled")
    if not config.candidate_pipeline.enrichment_enabled:
        pipeline_issues.append("Candidate Enrichment disabled")
    
    if pipeline_issues:
        warnings.append(f"
         Pipeline components disabled: {', '.join(pipeline_issues)}")
    else:
        print(" All pipeline components enabled")
    
    # Print results
    print("\n" + "=" * 60)
    print("PRODUCTION READINESS SUMMARY")
    print("=" * 60)
    
    if critical_issues:
        print(" CRITICAL ISSUES (Must fix before production):")
        for issue in critical_issues:
            print(f"   {issue}")
        print()
    
    if warnings:
        print("
         WARNINGS (Review before production):")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not critical_issues and not warnings:
        print(" PRODUCTION READY!")
        print(" All critical components configured")
        print(" No warnings detected")
        return True
    elif not critical_issues:
        print(" MOSTLY READY (Minor warnings)")
        print(" All critical components configured")
        print("
         Some warnings to review")
        return True
    else:
        print(" NOT PRODUCTION READY")
        print(" Critical issues must be resolved")
        return False

def generate_todo_checklist():
    """Generate a TODO checklist for production deployment"""
    
    config = get_config()
    
    print("\n PRODUCTION DEPLOYMENT TODO CHECKLIST")
    print("=" * 60)
    
    todos = []
    
    # API Keys
    if not config.openai.api_key or config.openai.api_key == "your_openai_api_key_here":
        todos.append(" Obtain and configure OpenAI API key in .env file")
    
    if config.linkedin.account_id == "your_linkedin_account_id_here":
        todos.append(" Update LINKEDIN_ACCOUNT_ID with your actual account ID")
    
    # Email configuration
    if "your_email@gmail.com" in os.getenv("EMAIL_USERNAME", ""):
        todos.append(" Configure email settings for candidate outreach")
    
    # Environment settings
    if config.debug:
        todos.append(" Set DEBUG=False for production deployment")
    
    # Optional enhancements
    if not config.candidate_pipeline.profile_scraping_enabled:
        todos.append(" Consider enabling ProfileScrapingAgent when ready (PROFILE_SCRAPING_ENABLED=True)")
    
    # Infrastructure
    todos.append(" Test database connection with real MongoDB instance")
    todos.append(" Test LinkedIn API connectivity with real search")
    todos.append(" Set up monitoring and alerting for production")
    todos.append(" Configure production logging and audit trails")
    todos.append(" Review security settings and access controls")
    todos.append(" Run full integration tests with real data")
    todos.append(" Configure performance monitoring and metrics")
    todos.append(" Set up error tracking and notification system")
    
    if not todos:
        print(" No outstanding TODOs - system appears production ready!")
    else:
        for i, todo in enumerate(todos, 1):
            print(f"{i:2d}. {todo}")
    
    print("\n PRIORITY ORDER:")
    print("   1. API Keys (Critical)")
    print("   2. Database Testing (Critical)")  
    print("   3. Environment Settings (Important)")
    print("   4. Monitoring Setup (Important)")
    print("   5. Security Review (Important)")
    print("   6. Optional Enhancements (Nice to have)")
    
    return todos

if __name__ == "__main__":
    print(" UNIFIED SOURCING MANAGER CONFIGURATION CHECK")
    print("=" * 80)
    
    # Show current configuration
    print_config_summary()
    print("\n")
    
    # Check production readiness
    is_ready = check_production_readiness()
    
    # Generate TODO checklist
    todos = generate_todo_checklist()
    
    print("\n" + "=" * 80)
    print(" FINAL ASSESSMENT")
    print("=" * 80)
    
    if is_ready:
        print(" Your Unified Sourcing Manager is ready for production!")
        print(" All critical components are properly configured")
        if todos:
            print(f" {len(todos)} optional improvements available (see checklist above)")
        else:
            print(" No outstanding issues - ready to deploy!")
    else:
        print("
         System requires configuration before production use")
        print(f" {len(todos)} items to address (see checklist above)")
        print(" Update your .env file with the required configuration")
    
    print(f"\n Configuration checked at: {os.popen('date').read().strip()}")
    print(" Tip: Run 'python config.py' to see detailed configuration")
    print(" Tip: Run 'python test_unified_sourcing_manager.py' to test functionality")