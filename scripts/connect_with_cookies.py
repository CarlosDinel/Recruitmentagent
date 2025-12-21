#!/usr/bin/env python3
"""
Connect LinkedIn Account via Unipile API using Cookies

⚠️  SECURITY WARNING: This script uses sensitive LinkedIn cookies.
    Do NOT commit these cookies to git or share them publicly!

Usage:
    # Option 1: Set environment variables
    export LINKEDIN_LI_AT='your-li-at-cookie'
    export LINKEDIN_LI_A='your-li-a-cookie'
    export LINKEDIN_IP='your-ip-address'
    export LINKEDIN_USER_AGENT='your-user-agent'
    python3 scripts/connect_with_cookies.py
    
    # Option 2: Pass as arguments (less secure)
    python3 scripts/connect_with_cookies.py --li-at 'cookie' --li-a 'cookie' --ip 'ip' --user-agent 'ua'
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.connect_linkedin_account import connect_with_cookies

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Connect LinkedIn account to Unipile using cookies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variables (recommended)
  export LINKEDIN_LI_AT='your-cookie'
  python3 scripts/connect_with_cookies.py
  
  # Using command line arguments
  python3 scripts/connect_with_cookies.py --li-at 'cookie' --li-a 'cookie'
  
⚠️  SECURITY: Never commit cookies to git or share them publicly!
        """
    )
    
    parser.add_argument(
        '--li-at',
        type=str,
        help='LinkedIn li_at cookie (or set LINKEDIN_LI_AT env var)',
        default=os.getenv('LINKEDIN_LI_AT')
    )
    parser.add_argument(
        '--li-a',
        type=str,
        help='LinkedIn li_a cookie (optional, or set LINKEDIN_LI_A env var)',
        default=os.getenv('LINKEDIN_LI_A')
    )
    parser.add_argument(
        '--ip',
        type=str,
        help='IP address (optional, or set LINKEDIN_IP env var)',
        default=os.getenv('LINKEDIN_IP')
    )
    parser.add_argument(
        '--user-agent',
        type=str,
        help='User agent string (optional, or set LINKEDIN_USER_AGENT env var)',
        default=os.getenv('LINKEDIN_USER_AGENT')
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("LINKEDIN_API_KEY")
    if not api_key:
        print("❌ LINKEDIN_API_KEY not found in .env file")
        print("   Please add your Unipile API key to .env file")
        return 1
    
    if not args.li_at:
        print("❌ LinkedIn li_at cookie is required")
        print()
        print("Provide it via:")
        print("  1. Environment variable: export LINKEDIN_LI_AT='your-cookie'")
        print("  2. Command line: --li-at 'your-cookie'")
        return 1
    
    # Connect with cookies
    result = connect_with_cookies(
        api_key=api_key,
        li_at=args.li_at,
        li_a=args.li_a,
        ip_address=args.ip,
        user_agent=args.user_agent
    )
    
    if result.get("account_id") or result.get("id"):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

