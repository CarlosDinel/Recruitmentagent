#!/usr/bin/env python3
"""
Connect LinkedIn Account via Unipile API

This script helps you connect your LinkedIn account to Unipile and get the account_id.
Based on Unipile API Reference: https://developer.unipile.com/reference/accountscontroller_createaccount

Usage:
    python scripts/connect_linkedin_account.py
"""

import os
import sys
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def connect_linkedin_account_native(
    api_key: str,
    li_at: str,
    li_a: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    base_url: str = "https://api4.unipile.com:13447/api/v1",
    provider: str = "linkedin",
    account_type: str = "linkedin"
) -> Dict[str, Any]:
    """
    Connect LinkedIn account using native authentication with cookies.
    
    According to Unipile API Reference:
    https://developer.unipile.com/reference/accountscontroller_createaccount
    
    Args:
        api_key: Your Unipile API key
        li_at: LinkedIn authentication cookie (li_at)
        li_a: LinkedIn authentication cookie (li_a) - optional
        ip_address: IP address used for authentication - optional
        user_agent: Browser user agent - optional
        base_url: Unipile API base URL
        provider: Provider type (default: "linkedin")
        account_type: Account type (default: "linkedin")
    
    Returns:
        Dictionary with account connection result including account_id
    """
    url = f"{base_url}/accounts"
    
    headers = {
        "accept": "application/json",
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    # Build request body according to Unipile API schema
    # For cookie authentication, provider must be "LINKEDIN" (uppercase)
    # access_token = li_at cookie, premium_token = li_a cookie
    data = {
        "provider": "LINKEDIN",  # Must be uppercase
        "access_token": li_at,  # li_at cookie value
    }
    
    # Add optional fields if provided
    if li_a:
        data["premium_token"] = li_a  # li_a cookie value
    if ip_address:
        data["ip"] = ip_address
    if user_agent:
        data["user_agent"] = user_agent
    
    try:
        print(f"🔗 Connecting LinkedIn account via Unipile API (Native Auth)...")
        print(f"   URL: {url}")
        print(f"   Provider: {provider}")
        print(f"   Using: li_at cookie")
        if li_a:
            print(f"   Using: li_a cookie")
        if ip_address:
            print(f"   Using: IP address")
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if "account_id" in result or "id" in result:
            account_id = result.get("account_id") or result.get("id")
            print(f"✅ LinkedIn account connected successfully!")
            print(f"   Account ID: {account_id}")
            return result
        else:
            print(f"⚠️  Account connected but no account_id in response")
            print(f"   Response: {result}")
            return result
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Details: {error_detail}")
            except:
                print(f"   Response: {e.response.text}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ Error connecting account: {e}")
        return {"success": False, "error": str(e)}


def list_connected_accounts(
    api_key: str,
    base_url: str = "https://api4.unipile.com:13447/api/v1"
) -> Dict[str, Any]:
    """
    List all connected accounts to find your LinkedIn account_id.
    
    According to Unipile API Reference:
    GET /api/v1/accounts
    
    Args:
        api_key: Your Unipile API key
        base_url: Unipile API base URL
    
    Returns:
        List of connected accounts
    """
    url = f"{base_url}/accounts"
    
    headers = {
        "accept": "application/json",
        "X-API-KEY": api_key
    }
    
    try:
        print(f"📋 Fetching connected accounts from Unipile...")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Handle different response formats
        accounts = result.get("items", result.get("accounts", result.get("data", [])))
        
        if isinstance(result, list):
            accounts = result
        
        print(f"✅ Found {len(accounts)} connected account(s)")
        
        # Show all account types for debugging
        if accounts:
            account_types = {}
            for acc in accounts:
                acc_type = acc.get("provider") or acc.get("type") or "unknown"
                account_types[acc_type] = account_types.get(acc_type, 0) + 1
            print(f"\n📊 Account types found:")
            for acc_type, count in account_types.items():
                print(f"   - {acc_type}: {count} account(s)")
        
        # Filter LinkedIn accounts
        linkedin_accounts = [
            acc for acc in accounts 
            if (acc.get("provider", "").lower() == "linkedin" or 
                acc.get("type", "").lower() == "linkedin" or
                "linkedin" in str(acc.get("provider", "")).lower() or
                "linkedin" in str(acc.get("type", "")).lower())
        ]
        
        if linkedin_accounts:
            print(f"\n📌 LinkedIn Account(s) Found:")
            print("-" * 70)
            for i, acc in enumerate(linkedin_accounts, 1):
                account_id = acc.get("account_id") or acc.get("id") or acc.get("_id", "N/A")
                status = acc.get("status", "unknown")
                provider = acc.get("provider") or acc.get("type", "unknown")
                print(f"   {i}. Account ID: {account_id}")
                print(f"      Provider: {provider}")
                print(f"      Status: {status}")
                if acc.get("name"):
                    print(f"      Name: {acc.get('name')}")
                print()
        else:
            print(f"\n⚠️  No LinkedIn accounts found")
            print(f"   You have {len(accounts)} other account(s) connected")
            print(f"   You need to connect a LinkedIn account specifically")
        
        return {"accounts": accounts, "linkedin_accounts": linkedin_accounts}
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Details: {error_detail}")
            except:
                print(f"   Response: {e.response.text}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ Error fetching accounts: {e}")
        return {"success": False, "error": str(e)}


def connect_with_cookies(
    api_key: str,
    li_at: str,
    li_a: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Connect LinkedIn account using provided cookies.
    
    Args:
        api_key: Unipile API key
        li_at: LinkedIn li_at cookie
        li_a: LinkedIn li_a cookie (optional)
        ip_address: IP address (optional)
        user_agent: User agent string (optional)
    
    Returns:
        Connection result with account_id
    """
    base_url = os.getenv("LINKEDIN_BASE_URL", "https://api4.unipile.com:13447/api/v1")
    
    print("=" * 70)
    print("CONNECTING LINKEDIN ACCOUNT WITH COOKIES")
    print("=" * 70)
    print()
    print("⚠️  SECURITY WARNING:")
    print("   These cookies are sensitive! Do not share or commit them.")
    print()
    
    result = connect_linkedin_account_native(
        api_key=api_key,
        li_at=li_at,
        li_a=li_a,
        ip_address=ip_address,
        user_agent=user_agent,
        base_url=base_url
    )
    
    if result.get("account_id") or result.get("id"):
        account_id = result.get("account_id") or result.get("id")
        print()
        print("=" * 70)
        print("✅ SUCCESS! Add this to your .env file:")
        print("=" * 70)
        print()
        print(f'LINKEDIN_ACCOUNT_ID="{account_id}"')
        print()
        print("⚠️  Remember to remove the cookies from your code after use!")
        print("=" * 70)
    
    return result


def main():
    """Main function to help user connect LinkedIn account."""
    print("=" * 70)
    print("UNIPILE LINKEDIN ACCOUNT CONNECTION HELPER")
    print("=" * 70)
    print()
    
    # Get API key from environment
    api_key = os.getenv("LINKEDIN_API_KEY")
    if not api_key:
        print("❌ LINKEDIN_API_KEY not found in .env file")
        print("   Please add your Unipile API key to .env file")
        return 1
    
    base_url = os.getenv("LINKEDIN_BASE_URL", "https://api4.unipile.com:13447/api/v1")
    
    print(f"✅ Using API Key: {api_key[:20]}...")
    print(f"✅ Base URL: {base_url}")
    print()
    
    # Check if cookies are provided via environment or command line
    li_at = os.getenv("LINKEDIN_LI_AT")
    li_a = os.getenv("LINKEDIN_LI_A")
    ip_address = os.getenv("LINKEDIN_IP")
    user_agent = os.getenv("LINKEDIN_USER_AGENT")
    
    # If cookies provided, try to connect
    if li_at:
        print("🔐 LinkedIn cookies found in environment variables")
        print("   Attempting to connect account...")
        print()
        result = connect_with_cookies(
            api_key=api_key,
            li_at=li_at,
            li_a=li_a,
            ip_address=ip_address,
            user_agent=user_agent
        )
        if result.get("account_id") or result.get("id"):
            return 0
    
    # First, try to list existing accounts
    print("Step 1: Checking for existing connected accounts...")
    print("-" * 70)
    accounts_result = list_connected_accounts(api_key, base_url)
    
    if accounts_result.get("linkedin_accounts"):
        print()
        print("=" * 70)
        print("✅ FOUND LINKEDIN ACCOUNT(S)!")
        print("=" * 70)
        print()
        print("Copy one of the Account IDs above and add it to your .env file:")
        print()
        for acc in accounts_result["linkedin_accounts"]:
            account_id = acc.get("account_id") or acc.get("id") or acc.get("_id")
            if account_id:
                print(f'LINKEDIN_ACCOUNT_ID="{account_id}"')
        print()
        return 0
    
    # If no accounts found, provide instructions
    print()
    print("=" * 70)
    print("⚠️  NO LINKEDIN ACCOUNTS FOUND")
    print("=" * 70)
    print()
    print("You need to connect a LinkedIn account first.")
    print()
    print("OPTION 1: Via Unipile Dashboard (Recommended)")
    print("-" * 70)
    print("1. Go to: https://unipile.com")
    print("2. Log in to your dashboard")
    print("3. Go to: Integration → Hosted auth wizard")
    print("4. Follow: LinkedIn Authentication Setup")
    print("5. Connect your LinkedIn account")
    print("6. Copy the account_id from Connected Accounts")
    print()
    print("OPTION 2: Via API with Cookies (Advanced)")
    print("-" * 70)
    print("If you have LinkedIn cookies (li_at, li_a), you can use:")
    print()
    print("  export LINKEDIN_LI_AT='your-li-at-cookie'")
    print("  export LINKEDIN_LI_A='your-li-a-cookie'  # optional")
    print("  export LINKEDIN_IP='your-ip'  # optional")
    print("  export LINKEDIN_USER_AGENT='your-user-agent'  # optional")
    print("  python3 scripts/connect_linkedin_account.py")
    print()
    print("⚠️  SECURITY: Never commit cookies to git!")
    print()
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

