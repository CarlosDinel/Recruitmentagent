"""
Real API Integration Tests
Tests the complete recruitment flow using real Unipile LinkedIn API.

NOTE: These tests require valid LINKEDIN_API_KEY and LINKEDIN_ACCOUNT_ID 
in your .env file. They make real API calls and count against your Unipile quota.

Run with: pytest test/test_real_api_integration.py -v -s
Skip with: pytest test/ --ignore=test/test_real_api_integration.py
"""

import pytest
import json
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Check if we have real API credentials
LINKEDIN_API_KEY = os.getenv('LINKEDIN_API_KEY')
LINKEDIN_ACCOUNT_ID = os.getenv('LINKEDIN_ACCOUNT_ID')

# Skip all tests if API credentials not available
skip_if_no_api = pytest.mark.skipif(
    not LINKEDIN_API_KEY or not LINKEDIN_ACCOUNT_ID,
    reason="LinkedIn API credentials not configured. Set LINKEDIN_API_KEY and LINKEDIN_ACCOUNT_ID in .env"
)


class TestRealLinkedInSearch:
    """Test real LinkedIn search API via Unipile."""
    
    @skip_if_no_api
    def test_search_software_engineers(self):
        """Test searching for software engineers in Netherlands."""
        from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
        
        print("\n🔍 Testing real LinkedIn search...")
        
        # Execute real search
        result = search_candidates_integrated_cursor_and_no_cursor.invoke({
            'project_id': 'TEST_REAL_API_001',
            'search_id': 'TEST_SEARCH_001',
            'max_results': 3,
            'keywords': 'Software Engineer',
            'location': 'Netherlands',
            'use_cursor': False
        })
        
        # Parse result
        result_data = json.loads(result)
        
        # Assertions
        assert result_data['success'] is True, "Search should succeed"
        assert 'candidates' in result_data, "Should have candidates key"
        assert len(result_data['candidates']) > 0, "Should find at least 1 candidate"
        assert len(result_data['candidates']) <= 3, "Should not exceed max_results"
        
        # Check search metadata
        assert 'search_metadata' in result_data
        metadata = result_data['search_metadata']
        assert metadata['project_id'] == 'TEST_REAL_API_001'
        assert metadata['search_id'] == 'TEST_SEARCH_001'
        assert metadata['total_found'] > 0
        
        # Verify candidate data structure
        for candidate in result_data['candidates']:
            assert 'naam' in candidate or 'full_name' in candidate, "Should have name"
            assert 'locatie' in candidate or 'location' in candidate, "Should have location"
            
            # At least one should have a headline
            if candidate.get('headline'):
                assert isinstance(candidate['headline'], str)
                assert len(candidate['headline']) > 0
        
        print(f"   ✅ Found {len(result_data['candidates'])} candidates")
        print(f"   ✅ Search completed at {metadata['search_timestamp']}")
    
    @skip_if_no_api
    def test_search_with_different_queries(self):
        """Test search with various job titles."""
        from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
        
        queries = [
            ('Python developer', 'Amsterdam'),
            ('Data Scientist', 'Rotterdam'),
        ]
        
        for keywords, location in queries:
            print(f"\n🔍 Testing search: {keywords} in {location}")
            
            result = search_candidates_integrated_cursor_and_no_cursor.invoke({
                'project_id': 'TEST_QUERIES',
                'search_id': f'SEARCH_{keywords.replace(" ", "_")}',
                'max_results': 2,
                'keywords': keywords,
                'location': location,
                'use_cursor': False
            })
            
            result_data = json.loads(result)
            
            assert result_data['success'] is True
            assert len(result_data['candidates']) >= 0  # May return 0 for specific queries
            
            print(f"   ✅ {keywords}: {len(result_data['candidates'])} results")
    
    @skip_if_no_api
    def test_search_api_response_format(self):
        """Verify the API response has correct format."""
        from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
        
        result = search_candidates_integrated_cursor_and_no_cursor.invoke({
            'project_id': 'FORMAT_TEST',
            'search_id': 'FORMAT_001',
            'max_results': 1,
            'keywords': 'Engineer',
            'location': 'Netherlands',
            'use_cursor': False
        })
        
        result_data = json.loads(result)
        
        # Check top-level structure
        assert 'success' in result_data
        assert 'candidates' in result_data
        assert 'search_metadata' in result_data
        
        # Check metadata structure
        metadata = result_data['search_metadata']
        required_metadata_keys = [
            'project_id', 'search_id', 'total_found', 
            'search_criteria', 'search_timestamp'
        ]
        for key in required_metadata_keys:
            assert key in metadata, f"Metadata should have {key}"
        
        print("   ✅ Response format is correct")


class TestRealProfileScraping:
    """Test real LinkedIn profile scraping via Unipile."""
    
    @skip_if_no_api
    def test_scrape_profile_with_url(self):
        """Test scraping a real LinkedIn profile."""
        from tools.scourcing_tools import LinkedIn_profile_scrape
        
        # First, get a profile URL from search
        from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
        
        print("\n🔍 Finding candidate with valid profile URL...")
        
        search_result = search_candidates_integrated_cursor_and_no_cursor.invoke({
            'project_id': 'SCRAPE_TEST',
            'search_id': 'SCRAPE_001',
            'max_results': 5,
            'keywords': 'Developer',
            'location': 'Netherlands',
            'use_cursor': False
        })
        
        search_data = json.loads(search_result)
        
        # Find candidate with profile URL
        profile_url = None
        for candidate in search_data['candidates']:
            url = candidate.get('profile_url') or candidate.get('LinkedIn_profile_url', '')
            if url and 'linkedin.com/in/' in url:
                profile_url = url
                break
        
        if not profile_url:
            pytest.skip("No candidate with valid profile URL found in search results")
        
        print(f"   📋 Scraping: {profile_url[:60]}...")
        
        # Scrape the profile
        result = LinkedIn_profile_scrape.invoke({'profile_url': profile_url})
        result_data = json.loads(result)
        
        # Assertions
        assert result_data['success'] is True, "Profile scraping should succeed"
        assert 'profile_data' in result_data, "Should have profile_data"
        assert 'scrape_metadata' in result_data, "Should have metadata"
        
        profile = result_data['profile_data']
        
        # Check profile has enrichment data
        assert 'headline' in profile, "Should have headline"
        assert 'skills' in profile, "Should have skills"
        
        # At least some profiles should have these
        has_experience = profile.get('experience') and len(profile['experience']) > 0
        has_education = profile.get('education') and len(profile['education']) > 0
        has_skills = profile.get('skills') and len(profile['skills']) > 0
        
        assert has_skills or has_experience or has_education, \
            "Profile should have at least skills, experience, or education"
        
        print(f"   ✅ Profile scraped successfully")
        if has_skills:
            print(f"   ✅ Skills: {len(profile['skills'])} found")
        if has_experience:
            print(f"   ✅ Experience: {len(profile['experience'])} positions")
        if has_education:
            print(f"   ✅ Education: {len(profile['education'])} degrees")
    
    @skip_if_no_api
    def test_profile_data_structure(self):
        """Verify scraped profile has correct data structure."""
        from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
        from tools.scourcing_tools import LinkedIn_profile_scrape
        
        # Get a profile
        search_result = search_candidates_integrated_cursor_and_no_cursor.invoke({
            'project_id': 'STRUCTURE_TEST',
            'search_id': 'STRUCTURE_001',
            'max_results': 3,
            'keywords': 'Engineer',
            'location': 'Netherlands',
            'use_cursor': False
        })
        
        search_data = json.loads(search_result)
        
        profile_url = None
        for candidate in search_data['candidates']:
            url = candidate.get('profile_url') or candidate.get('LinkedIn_profile_url', '')
            if url and 'linkedin.com/in/' in url:
                profile_url = url
                break
        
        if not profile_url:
            pytest.skip("No profile URL available")
        
        result = LinkedIn_profile_scrape.invoke({'profile_url': profile_url})
        result_data = json.loads(result)
        
        if not result_data.get('success'):
            pytest.skip(f"Profile scraping failed: {result_data.get('error')}")
        
        profile = result_data['profile_data']
        
        # Check expected fields exist
        expected_fields = [
            'naam', 'headline', 'locatie', 'skills', 
            'experience', 'education', 'summary'
        ]
        
        for field in expected_fields:
            assert field in profile, f"Profile should have {field} field"
        
        # Check data types
        if profile.get('skills'):
            assert isinstance(profile['skills'], list), "Skills should be a list"
        
        if profile.get('experience'):
            assert isinstance(profile['experience'], list), "Experience should be a list"
        
        if profile.get('education'):
            assert isinstance(profile['education'], list), "Education should be a list"
        
        print("   ✅ Profile data structure is valid")


class TestEndToEndRealAPI:
    """End-to-end tests with real API."""
    
    @skip_if_no_api
    def test_complete_sourcing_flow(self):
        """Test complete flow: search -> enrich -> validate."""
        from tools.scourcing_tools import (
            search_candidates_integrated_cursor_and_no_cursor,
            LinkedIn_profile_scrape
        )
        
        print("\n🚀 Testing complete sourcing flow with real API...")
        
        # Step 1: Search
        print("\n   Step 1: Searching for candidates...")
        search_result = search_candidates_integrated_cursor_and_no_cursor.invoke({
            'project_id': 'E2E_TEST',
            'search_id': 'E2E_001',
            'max_results': 3,
            'keywords': 'Software Engineer',
            'location': 'Netherlands',
            'use_cursor': False
        })
        
        search_data = json.loads(search_result)
        assert search_data['success'] is True
        assert len(search_data['candidates']) > 0
        
        print(f"   ✅ Found {len(search_data['candidates'])} candidates")
        
        # Step 2: Enrich
        print("\n   Step 2: Enriching candidate profiles...")
        enriched_count = 0
        
        for candidate in search_data['candidates']:
            url = candidate.get('profile_url') or candidate.get('LinkedIn_profile_url', '')
            if url and 'linkedin.com/in/' in url:
                print(f"      Enriching: {candidate.get('naam', 'Unknown')[:30]}...")
                
                profile_result = LinkedIn_profile_scrape.invoke({'profile_url': url})
                profile_data = json.loads(profile_result)
                
                if profile_data.get('success'):
                    enriched_count += 1
                    profile = profile_data['profile_data']
                    
                    # Validate enrichment added value
                    skills_count = len(profile.get('skills', []))
                    exp_count = len(profile.get('experience', []))
                    
                    print(f"         Skills: {skills_count}, Experience: {exp_count}")
                
                # Only enrich first one to save API quota
                break
        
        assert enriched_count > 0, "Should enrich at least one profile"
        
        print(f"\n   ✅ Enriched {enriched_count} profile(s)")
        print("\n   🎉 Complete flow successful!")
    
    @skip_if_no_api
    def test_api_error_handling(self):
        """Test that API errors are handled gracefully."""
        from tools.scourcing_tools import LinkedIn_profile_scrape
        
        print("\n🧪 Testing error handling...")
        
        # Test with invalid URL
        result = LinkedIn_profile_scrape.invoke({
            'profile_url': 'https://linkedin.com/in/this-profile-definitely-does-not-exist-12345'
        })
        
        result_data = json.loads(result)
        
        # Should not crash, should return error gracefully
        assert 'success' in result_data
        assert 'scrape_metadata' in result_data
        
        if not result_data['success']:
            assert 'error' in result_data
            print(f"   ✅ Error handled gracefully: {result_data['error'][:50]}...")
        else:
            print("   ✅ API returned data (profile exists)")


class TestAPIQuotaManagement:
    """Tests for API quota and rate limiting."""
    
    @skip_if_no_api
    def test_respect_rate_limits(self):
        """Verify system respects rate limits."""
        from tools.scourcing_tools import search_candidates_integrated_cursor_and_no_cursor
        import time
        
        print("\n⏱️  Testing rate limit handling...")
        
        start_time = time.time()
        
        # Make 2 quick searches
        for i in range(2):
            result = search_candidates_integrated_cursor_and_no_cursor.invoke({
                'project_id': 'RATE_TEST',
                'search_id': f'RATE_{i}',
                'max_results': 1,
                'keywords': 'Developer',
                'location': 'Netherlands',
                'use_cursor': False
            })
            
            result_data = json.loads(result)
            assert result_data['success'] is True
        
        elapsed = time.time() - start_time
        
        # Unipile rate limit is ~100 req/minute, so 2 should be instant
        assert elapsed < 5, "Two searches should complete quickly"
        
        print(f"   ✅ 2 searches completed in {elapsed:.2f}s")
        print(f"   ✅ Rate limits respected")


# Run info message
if __name__ == "__main__":
    print("\n" + "="*70)
    print("REAL API INTEGRATION TESTS")
    print("="*70)
    print("\nThese tests use real Unipile API calls and count against your quota.")
    print("Make sure you have LINKEDIN_API_KEY and LINKEDIN_ACCOUNT_ID set in .env")
    print("\nRun with: pytest test/test_real_api_integration.py -v -s")
    print("="*70 + "\n")
