"""
Unit tests for Profile Scraping Agent.

Tests cover profile enrichment, caching, error handling, and batch processing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from sub_agents.profile_scraping_agent import ProfileScrapingAgent


class TestProfileScrapingAgent:
    """Test suite for ProfileScrapingAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a ProfileScrapingAgent instance for testing."""
        return ProfileScrapingAgent()
    
    @pytest.fixture
    def sample_candidates(self):
        """Sample candidates for testing."""
        return [
            {
                "full_name": "John Doe",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "current_position": "Senior Developer",
                "current_company": "Tech Corp",
                "skills": ["Python", "AWS"]
            },
            {
                "full_name": "Jane Smith",
                "linkedin_url": "https://linkedin.com/in/janesmith",
                "current_position": "Data Scientist",
                "current_company": "Data Inc",
                "skills": ["Python", "ML"]
            }
        ]
    
    @pytest.fixture
    def sample_profile_data(self):
        """Sample enriched profile data."""
        return {
            "work_experience": [
                {
                    "company": "Tech Corp",
                    "position": "Senior Developer",
                    "duration": "2020-Present",
                    "description": "Leading backend development"
                }
            ],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "BSc Computer Science",
                    "year": "2018"
                }
            ],
            "skills": ["Python", "AWS", "Docker", "Kubernetes"],
            "certifications": ["AWS Certified Solutions Architect"],
            "languages": ["English", "Spanish"],
            "endorsements": {"Python": 25, "AWS": 18},
            "summary": "Experienced software engineer with 5+ years",
            "headline": "Senior Software Engineer at Tech Corp",
            "connections_count": 500
        }
    
    @pytest.fixture
    def sourcing_manager_request(self, sample_candidates):
        """Sample request from Sourcing Manager."""
        return {
            "candidates": sample_candidates,
            "projectid": "PROJ-2025-001",
            "naam_project": "Backend Team Expansion",
            "campaign_num": "CAMP-001",
            "search_id": "SEARCH-001"
        }
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent.name == "Profile Scraping Agent"
        assert agent.role == "Detailed LinkedIn profile scraping and enrichment"
        assert agent.config["max_retries"] == 3
        assert agent.config["enable_caching"] is True
        assert isinstance(agent._profile_cache, dict)
    
    def test_enrich_candidates_success(self, agent, sourcing_manager_request, sample_profile_data):
        """Test successful candidate enrichment."""
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            # Mock the scraping tool to return success
            mock_scrape.invoke.return_value = json.dumps({
                "success": True,
                "profile_data": sample_profile_data
            })
            
            result = agent.enrich_candidates(sourcing_manager_request)
            
            assert result["success"] is True
            assert len(result["enriched_candidates"]) == 2
            assert result["enrichment_stats"]["success_count"] == 2
            assert result["enrichment_stats"]["failed_count"] == 0
            assert result["enrichment_stats"]["success_rate"] == 1.0
    
    def test_enrich_candidates_with_failures(self, agent, sourcing_manager_request, sample_profile_data):
        """Test enrichment with some failures."""
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            # First call succeeds, second fails
            mock_scrape.invoke.side_effect = [
                json.dumps({"success": True, "profile_data": sample_profile_data}),
                json.dumps({"success": False, "error": "Rate limit exceeded"})
            ]
            
            result = agent.enrich_candidates(sourcing_manager_request)
            
            assert result["success"] is True
            assert result["enrichment_stats"]["success_count"] == 1
            assert result["enrichment_stats"]["failed_count"] == 1
            assert len(result["enriched_candidates"]) == 1
            assert len(result["failed_enrichments"]) == 1
    
    def test_enrich_candidates_no_linkedin_url(self, agent):
        """Test handling of candidates without LinkedIn URLs."""
        request = {
            "candidates": [
                {"full_name": "John Doe", "email": "john@example.com"}
            ],
            "projectid": "PROJ-001"
        }
        
        result = agent.enrich_candidates(request)
        
        assert result["success"] is True
        assert result["enrichment_stats"]["failed_count"] == 1
        assert "No LinkedIn URL" in result["failed_enrichments"][0]["enrichment_error"]
    
    def test_enrich_candidates_empty_list(self, agent):
        """Test handling of empty candidate list."""
        request = {
            "candidates": [],
            "projectid": "PROJ-001"
        }
        
        result = agent.enrich_candidates(request)
        
        assert result["success"] is False
        assert "No candidates provided" in result["error"]
    
    def test_caching_mechanism(self, agent, sourcing_manager_request, sample_profile_data):
        """Test that caching works correctly."""
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            mock_scrape.invoke.return_value = json.dumps({
                "success": True,
                "profile_data": sample_profile_data
            })
            
            # First enrichment - should call scraping tool
            result1 = agent.enrich_candidates(sourcing_manager_request)
            assert mock_scrape.invoke.call_count == 2  # Two candidates
            assert len(result1["enriched_candidates"]) == 2
            
            # Check cache was populated
            assert agent.get_cache_size() == 2
            
            # Second enrichment - should use cache (mock still needs to be active)
            result2 = agent.enrich_candidates(sourcing_manager_request)
            assert len(result2["enriched_candidates"]) == 2
            
            # Check cache indicators
            assert result2["enriched_candidates"][0]["enrichment_source"] == "cache"
            assert result2["enriched_candidates"][1]["enrichment_source"] == "cache"
    
    def test_cache_clearing(self, agent):
        """Test cache clearing functionality."""
        agent._profile_cache["test_url"] = {"data": "test"}
        assert agent.get_cache_size() == 1
        
        agent.clear_cache()
        assert agent.get_cache_size() == 0
    
    def test_retry_logic(self, agent, sample_candidates, sample_profile_data):
        """Test retry logic on failures."""
        request = {
            "candidates": [sample_candidates[0]],
            "projectid": "PROJ-001"
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):  # Mock sleep to speed up test
            
            # Fail twice, then succeed
            mock_scrape.invoke.side_effect = [
                json.dumps({"success": False, "error": "Timeout"}),
                json.dumps({"success": False, "error": "Timeout"}),
                json.dumps({"success": True, "profile_data": sample_profile_data})
            ]
            
            result = agent.enrich_candidates(request)
            
            assert result["success"] is True
            assert result["enrichment_stats"]["success_count"] == 1
            assert mock_scrape.invoke.call_count == 3
    
    def test_retry_exhaustion(self, agent, sample_candidates):
        """Test behavior when all retries are exhausted."""
        request = {
            "candidates": [sample_candidates[0]],
            "projectid": "PROJ-001"
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):
            
            # All attempts fail
            mock_scrape.invoke.return_value = json.dumps({
                "success": False,
                "error": "Connection error"
            })
            
            result = agent.enrich_candidates(request)
            
            assert result["success"] is True
            assert result["enrichment_stats"]["failed_count"] == 1
            assert result["failed_enrichments"][0]["enrichment_status"] == "failed"
    
    def test_merge_enrichment_data(self, agent, sample_candidates, sample_profile_data):
        """Test merging of enrichment data with existing candidate data."""
        candidate = sample_candidates[0]
        
        enriched = agent._merge_enrichment_data(candidate, sample_profile_data, from_cache=False)
        
        # Check that original data is preserved
        assert enriched["full_name"] == "John Doe"
        assert enriched["current_position"] == "Senior Developer"
        
        # Check that new data is added
        assert "work_experience" in enriched
        assert "education" in enriched
        assert "certifications" in enriched
        
        # Check skills merge (should combine without duplicates)
        assert "Python" in enriched["skills"]
        assert "Docker" in enriched["skills"]
        assert len(enriched["skills"]) == len(set(enriched["skills"]))  # No duplicates
        
        # Check enrichment metadata
        assert enriched["enrichment_source"] == "live_scrape"
    
    def test_batch_processing(self, agent, sample_profile_data):
        """Test batch processing of candidates."""
        # Create more candidates than batch size
        many_candidates = [
            {
                "full_name": f"Candidate {i}",
                "linkedin_url": f"https://linkedin.com/in/candidate{i}",
                "skills": ["Python"]
            }
            for i in range(25)
        ]
        
        request = {
            "candidates": many_candidates,
            "projectid": "PROJ-001",
            "enrichment_config": {"batch_size": 10}
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):
            
            mock_scrape.invoke.return_value = json.dumps({
                "success": True,
                "profile_data": sample_profile_data
            })
            
            result = agent.enrich_candidates(request)
            
            assert result["success"] is True
            assert result["enrichment_stats"]["total_processed"] == 25
            assert mock_scrape.invoke.call_count == 25
    
    def test_custom_config_override(self, agent, sourcing_manager_request, sample_profile_data):
        """Test that custom config overrides default config."""
        sourcing_manager_request["enrichment_config"] = {
            "max_retries": 5,
            "batch_size": 5
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            mock_scrape.invoke.return_value = json.dumps({
                "success": True,
                "profile_data": sample_profile_data
            })
            
            # The enrichment should use custom config
            result = agent.enrich_candidates(sourcing_manager_request)
            assert result["success"] is True
    
    def test_project_metadata_extraction(self, agent):
        """Test extraction of project metadata."""
        request = {
            "projectid": "PROJ-123",
            "naam_project": "Test Project",
            "campaign_num": "CAMP-456",
            "search_id": "SEARCH-789"
        }
        
        metadata = agent._extract_project_metadata(request)
        
        assert metadata["project_id"] == "PROJ-123"
        assert metadata["project_name"] == "Test Project"
        assert metadata["campaign_num"] == "CAMP-456"
        assert metadata["search_id"] == "SEARCH-789"
    
    def test_exception_handling(self, agent, sourcing_manager_request):
        """Test handling of exceptions during scraping."""
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):
            
            # Simulate exception
            mock_scrape.invoke.side_effect = Exception("Network error")
            
            result = agent.enrich_candidates(sourcing_manager_request)
            
            assert result["success"] is True
            assert result["enrichment_stats"]["failed_count"] == 2
            assert all("error" in f["enrichment_error"].lower() 
                      for f in result["failed_enrichments"])
    
    def test_rate_limiting(self, agent, sample_candidates, sample_profile_data):
        """Test that rate limiting is applied between requests."""
        request = {
            "candidates": sample_candidates,
            "projectid": "PROJ-001",
            "enrichment_config": {"rate_limit_delay": 0.5}
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep') as mock_sleep:
            
            mock_scrape.invoke.return_value = json.dumps({
                "success": True,
                "profile_data": sample_profile_data
            })
            
            agent.enrich_candidates(request)
            
            # Check that sleep was called for rate limiting
            assert mock_sleep.call_count >= len(sample_candidates)


class TestProfileScrapingAgentIntegration:
    """Integration tests for Profile Scraping Agent."""
    
    @pytest.fixture
    def agent(self):
        return ProfileScrapingAgent()
    
    def test_end_to_end_enrichment_workflow(self, agent):
        """Test complete enrichment workflow with mocked LinkedIn API."""
        request = {
            "candidates": [
                {
                    "full_name": "Alice Johnson",
                    "linkedin_url": "https://linkedin.com/in/alicejohnson",
                    "current_position": "ML Engineer",
                    "skills": ["Python", "TensorFlow"]
                }
            ],
            "projectid": "PROJ-INTEGRATION-001",
            "naam_project": "AI Team Building",
            "campaign_num": "CAMP-INT-001"
        }
        
        enriched_data = {
            "work_experience": [{"company": "AI Corp", "position": "ML Engineer"}],
            "education": [{"institution": "Stanford", "degree": "MS AI"}],
            "skills": ["Python", "TensorFlow", "PyTorch", "MLOps"],
            "certifications": ["Google Cloud ML Engineer"],
            "languages": ["English"],
            "summary": "ML Engineer with 4 years experience"
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            mock_scrape.invoke.return_value = json.dumps({
                "success": True,
                "profile_data": enriched_data
            })
            
            result = agent.enrich_candidates(request)
            
            # Verify complete workflow
            assert result["success"] is True
            assert len(result["enriched_candidates"]) == 1
            
            enriched = result["enriched_candidates"][0]
            assert enriched["full_name"] == "Alice Johnson"
            assert "work_experience" in enriched
            assert "education" in enriched
            assert "PyTorch" in enriched["skills"]
            assert enriched["enrichment_status"] == "success"
            assert "enrichment_timestamp" in enriched
            assert enriched["project_metadata"]["project_id"] == "PROJ-INTEGRATION-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
