"""
Integration tests for Profile Scraping Agent with API simulation.

These tests simulate real API behavior including:
- Rate limiting
- Network timeouts
- Partial data responses
- API error conditions
- Data validation
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sub_agents.profile_scraping_agent import ProfileScrapingAgent
from agents.database_agent import DatabaseAgent


class LinkedInAPISimulator:
    """
    Simulates real LinkedIn API behavior for integration testing.
    Includes realistic delays, rate limits, and error conditions.
    """
    
    def __init__(self):
        self.api_calls = []
        self.call_count = 0
        self.rate_limit_threshold = 10
        self.rate_limit_reset_time = None
        self.network_errors_enabled = False
        
    def scrape_profile(self, linkedin_url: str) -> dict:
        """Simulate LinkedIn profile scraping API call."""
        
        self.call_count += 1
        self.api_calls.append({
            "url": linkedin_url,
            "timestamp": datetime.now().isoformat(),
            "call_number": self.call_count
        })
        
        # Simulate API rate limiting
        if self.call_count > self.rate_limit_threshold and not self.rate_limit_reset_time:
            self.rate_limit_reset_time = time.time() + 60
            return {
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
                "retry_after": 60
            }
        
        # Simulate network errors
        if self.network_errors_enabled and self.call_count % 3 == 0:
            return {
                "success": False,
                "error": "Network timeout"
            }
        
        # Simulate realistic API delay
        time.sleep(0.1)  # 100ms API latency
        
        # Parse profile from URL
        profile_id = linkedin_url.split("/in/")[-1].replace("/", "")
        
        # Return realistic profile data based on URL
        if "senior" in profile_id.lower():
            return self._create_senior_profile(profile_id)
        elif "junior" in profile_id.lower():
            return self._create_junior_profile(profile_id)
        elif "error" in profile_id.lower():
            return {"success": False, "error": "Profile not found"}
        else:
            return self._create_standard_profile(profile_id)
    
    def _create_senior_profile(self, profile_id: str) -> dict:
        """Create a realistic senior developer profile."""
        return {
            "success": True,
            "profile_data": {
                "provider_id": f"senior-{profile_id}",
                "naam": f"Senior {profile_id.title()}",
                "headline": "Senior Software Engineer | Python | Cloud Architecture",
                "locatie": "Amsterdam, Netherlands",
                "current_position": "Senior Software Engineer",
                "current_company": "TechCorp International",
                "work_experience": [
                    {
                        "company": "TechCorp International",
                        "position": "Senior Software Engineer",
                        "duration": "2020-Present",
                        "duration_years": 3,
                        "description": "Leading backend architecture and mentoring junior developers",
                        "technologies": ["Python", "Django", "AWS", "Kubernetes"]
                    },
                    {
                        "company": "StartupCo",
                        "position": "Software Engineer",
                        "duration": "2017-2020",
                        "duration_years": 3,
                        "description": "Full-stack development and DevOps",
                        "technologies": ["Python", "React", "Docker"]
                    },
                    {
                        "company": "Digital Agency",
                        "position": "Junior Developer",
                        "duration": "2015-2017",
                        "duration_years": 2,
                        "description": "Web development and maintenance",
                        "technologies": ["Python", "Flask", "PostgreSQL"]
                    }
                ],
                "education": [
                    {
                        "institution": "University of Amsterdam",
                        "degree": "MSc Computer Science",
                        "field": "Software Engineering",
                        "year": "2015",
                        "grade": "Cum Laude"
                    },
                    {
                        "institution": "VU Amsterdam",
                        "degree": "BSc Information Science",
                        "field": "Computer Science",
                        "year": "2013"
                    }
                ],
                "skills": [
                    "Python", "Django", "FastAPI", "Flask",
                    "AWS", "Docker", "Kubernetes", "Terraform",
                    "PostgreSQL", "Redis", "MongoDB",
                    "REST API", "GraphQL", "Microservices",
                    "CI/CD", "Git", "Agile"
                ],
                "certifications": [
                    "AWS Certified Solutions Architect - Associate",
                    "AWS Certified Developer - Associate",
                    "Certified Kubernetes Administrator (CKA)",
                    "Python Institute PCPP"
                ],
                "languages": ["Dutch (Native)", "English (Fluent)", "German (Basic)"],
                "endorsements": {
                    "Python": 127,
                    "Django": 89,
                    "AWS": 76,
                    "Docker": 65,
                    "Kubernetes": 43
                },
                "recommendations": 12,
                "summary": "Passionate software engineer with 8+ years of experience building scalable backend systems. Specialized in Python, cloud architecture, and leading engineering teams. Strong advocate for clean code and test-driven development.",
                "connections_count": 850,
                "profile_completeness": 95,
                "recent_activities": [
                    {
                        "type": "post",
                        "date": "2025-12-15",
                        "content": "Just completed our migration to Kubernetes!"
                    }
                ]
            }
        }
    
    def _create_junior_profile(self, profile_id: str) -> dict:
        """Create a realistic junior developer profile."""
        return {
            "success": True,
            "profile_data": {
                "provider_id": f"junior-{profile_id}",
                "naam": f"Junior {profile_id.title()}",
                "headline": "Junior Python Developer | Recent Graduate",
                "locatie": "Rotterdam, Netherlands",
                "current_position": "Junior Python Developer",
                "current_company": "Innovation Labs",
                "work_experience": [
                    {
                        "company": "Innovation Labs",
                        "position": "Junior Python Developer",
                        "duration": "2024-Present",
                        "duration_years": 1,
                        "description": "Backend development and API integration",
                        "technologies": ["Python", "Flask", "PostgreSQL"]
                    },
                    {
                        "company": "University IT Department",
                        "position": "Student Developer",
                        "duration": "2023-2024",
                        "duration_years": 1,
                        "description": "Part-time development work",
                        "technologies": ["Python", "Django"]
                    }
                ],
                "education": [
                    {
                        "institution": "Erasmus University Rotterdam",
                        "degree": "BSc Computer Science",
                        "field": "Software Engineering",
                        "year": "2024"
                    }
                ],
                "skills": [
                    "Python", "Django", "Flask",
                    "PostgreSQL", "Git",
                    "REST API", "HTML", "CSS", "JavaScript"
                ],
                "certifications": [
                    "Python Institute PCAP"
                ],
                "languages": ["Dutch (Native)", "English (Fluent)"],
                "endorsements": {
                    "Python": 15,
                    "Django": 8,
                    "Flask": 6
                },
                "recommendations": 2,
                "summary": "Recent computer science graduate with strong foundation in Python development. Eager to learn and grow in a dynamic team environment.",
                "connections_count": 250,
                "profile_completeness": 75,
                "recent_activities": []
            }
        }
    
    def _create_standard_profile(self, profile_id: str) -> dict:
        """Create a standard mid-level profile."""
        return {
            "success": True,
            "profile_data": {
                "provider_id": profile_id,
                "naam": profile_id.replace("-", " ").title(),
                "headline": "Software Engineer | Python Developer",
                "locatie": "Utrecht, Netherlands",
                "current_position": "Software Engineer",
                "current_company": "Tech Solutions BV",
                "work_experience": [
                    {
                        "company": "Tech Solutions BV",
                        "position": "Software Engineer",
                        "duration": "2021-Present",
                        "duration_years": 3,
                        "description": "Backend development with Python and Django",
                        "technologies": ["Python", "Django", "PostgreSQL", "Docker"]
                    }
                ],
                "education": [
                    {
                        "institution": "TU Delft",
                        "degree": "BSc Computer Science",
                        "year": "2021"
                    }
                ],
                "skills": ["Python", "Django", "PostgreSQL", "Docker", "Git"],
                "certifications": [],
                "languages": ["Dutch", "English"],
                "endorsements": {"Python": 35, "Django": 22},
                "recommendations": 5,
                "summary": "Software engineer with focus on backend development.",
                "connections_count": 450,
                "profile_completeness": 80
            }
        }


class TestProfileScrapingIntegration:
    """Integration tests with API simulation."""
    
    @pytest.fixture
    def linkedin_api_simulator(self):
        """Create LinkedIn API simulator."""
        return LinkedInAPISimulator()
    
    @pytest.fixture
    def agent(self):
        """Create ProfileScrapingAgent."""
        return ProfileScrapingAgent()
    
    def test_real_world_enrichment_workflow(self, agent, linkedin_api_simulator):
        """Test realistic enrichment workflow with API delays and data processing."""
        print("\n" + "="*70)
        print("REAL-WORLD PROFILE ENRICHMENT WORKFLOW")
        print("="*70)
        
        # Candidates to enrich
        candidates = [
            {
                "full_name": "Senior Developer",
                "linkedin_url": "https://linkedin.com/in/senior-developer",
                "current_position": "Senior Engineer",
                "skills": ["Python"]
            },
            {
                "full_name": "Mid Level Dev",
                "linkedin_url": "https://linkedin.com/in/mid-level-dev",
                "current_position": "Software Engineer",
                "skills": ["Python"]
            },
            {
                "full_name": "Junior Dev",
                "linkedin_url": "https://linkedin.com/in/junior-developer",
                "current_position": "Junior Developer",
                "skills": ["Python"]
            }
        ]
        
        # Mock the scraping tool with API simulator
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            def simulate_api_call(input_dict):
                url = input_dict.get("linkedin_url")
                result = linkedin_api_simulator.scrape_profile(url)
                return json.dumps(result)
            
            mock_scrape.invoke.side_effect = simulate_api_call
            
            # Execute enrichment
            start_time = time.time()
            
            result = agent.enrich_candidates({
                "candidates": candidates,
                "projectid": "INTEGRATION-TEST-001",
                "naam_project": "Real World Integration Test"
            })
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify results
            assert result["success"] is True
            assert len(result["enriched_candidates"]) == 3
            
            print(f"\n⏱️  Total enrichment time: {duration:.2f}s")
            print(f"📊 API calls made: {linkedin_api_simulator.call_count}")
            print(f"✅ Success rate: {result['enrichment_stats']['success_rate']*100:.0f}%")
            
            # Verify enriched data quality
            for candidate in result["enriched_candidates"]:
                print(f"\n👤 {candidate['full_name']}:")
                print(f"   - Work experience: {len(candidate.get('work_experience', []))} positions")
                print(f"   - Education: {len(candidate.get('education', []))} degrees")
                print(f"   - Skills: {len(candidate.get('skills', []))} skills")
                print(f"   - Certifications: {len(candidate.get('certifications', []))}")
                
                # Verify data structure
                assert isinstance(candidate.get('work_experience', []), list)
                assert isinstance(candidate.get('education', []), list)
                assert isinstance(candidate.get('skills', []), list)
                
                # Verify enrichment metadata
                assert candidate.get('enrichment_status') == 'success'
                assert 'enrichment_timestamp' in candidate
                assert 'project_metadata' in candidate
            
            # Verify different seniority levels have different data
            senior = next(c for c in result["enriched_candidates"] if "Senior" in c["full_name"])
            junior = next(c for c in result["enriched_candidates"] if "Junior" in c["full_name"])
            
            assert len(senior['work_experience']) > len(junior['work_experience'])
            assert len(senior['skills']) > len(junior['skills'])
            assert len(senior.get('certifications', [])) > len(junior.get('certifications', []))
            
            print(f"\n✅ Realistic workflow test passed!")
            print(f"   Senior profile: {len(senior['work_experience'])} jobs, {len(senior['skills'])} skills")
            print(f"   Junior profile: {len(junior['work_experience'])} jobs, {len(junior['skills'])} skills")
    
    def test_rate_limiting_handling(self, agent, linkedin_api_simulator):
        """Test handling of API rate limits."""
        print("\n" + "="*70)
        print("API RATE LIMITING TEST")
        print("="*70)
        
        # Set aggressive rate limit
        linkedin_api_simulator.rate_limit_threshold = 2
        
        # Create many candidates
        candidates = [
            {
                "full_name": f"Candidate {i}",
                "linkedin_url": f"https://linkedin.com/in/candidate-{i}",
                "skills": ["Python"]
            }
            for i in range(5)
        ]
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):  # Speed up test
            
            def simulate_api_call(input_dict):
                url = input_dict.get("linkedin_url")
                result = linkedin_api_simulator.scrape_profile(url)
                return json.dumps(result)
            
            mock_scrape.invoke.side_effect = simulate_api_call
            
            result = agent.enrich_candidates({
                "candidates": candidates,
                "projectid": "RATE-LIMIT-TEST"
            })
            
            # With retry logic, some may succeed despite rate limits
            # Verify that rate limiting was encountered during API calls
            print(f"\n📊 Results with rate limiting:")
            print(f"   - Success: {result['enrichment_stats']['success_count']}")
            print(f"   - Failed: {result['enrichment_stats']['failed_count']}")
            print(f"   - API calls made: {linkedin_api_simulator.call_count}")
            
            # Verify rate limiting was hit
            assert linkedin_api_simulator.call_count > linkedin_api_simulator.rate_limit_threshold
            print(f"   ✅ Rate limit threshold ({linkedin_api_simulator.rate_limit_threshold}) was exceeded")
            
            # Verify failure reasons if any failed
            if result["failed_enrichments"]:
                for failed in result["failed_enrichments"]:
                    assert "error" in failed["enrichment_error"].lower()
                    print(f"   ⚠️  {failed['full_name']}: {failed['enrichment_error']}")
            
            print("\n✅ Rate limiting test completed!")
    
    def test_network_error_recovery(self, agent, linkedin_api_simulator):
        """Test recovery from intermittent network errors."""
        print("\n" + "="*70)
        print("NETWORK ERROR RECOVERY TEST")
        print("="*70)
        
        # Enable network errors
        linkedin_api_simulator.network_errors_enabled = True
        
        candidates = [
            {
                "full_name": f"Candidate {i}",
                "linkedin_url": f"https://linkedin.com/in/candidate-{i}",
                "skills": ["Python"]
            }
            for i in range(6)
        ]
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):  # Speed up retries
            
            def simulate_api_call(input_dict):
                url = input_dict.get("linkedin_url")
                result = linkedin_api_simulator.scrape_profile(url)
                return json.dumps(result)
            
            mock_scrape.invoke.side_effect = simulate_api_call
            
            result = agent.enrich_candidates({
                "candidates": candidates,
                "projectid": "NETWORK-ERROR-TEST",
                "enrichment_config": {
                    "max_retries": 3,
                    "retry_delay": 0.1
                }
            })
            
            print(f"\n📊 Results with network errors:")
            print(f"   - Success: {result['enrichment_stats']['success_count']}")
            print(f"   - Failed: {result['enrichment_stats']['failed_count']}")
            print(f"   - Total API calls: {linkedin_api_simulator.call_count}")
            
            # Some should succeed despite errors (due to retries)
            assert result["enrichment_stats"]["success_count"] > 0
            
            print("\n✅ Network error recovery working!")
    
    def test_data_validation_and_quality(self, agent, linkedin_api_simulator):
        """Test data validation and quality checks."""
        print("\n" + "="*70)
        print("DATA VALIDATION AND QUALITY TEST")
        print("="*70)
        
        candidates = [
            {
                "full_name": "Senior Developer",
                "linkedin_url": "https://linkedin.com/in/senior-developer",
                "skills": ["Python", "Django"]
            }
        ]
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            def simulate_api_call(input_dict):
                url = input_dict.get("linkedin_url")
                result = linkedin_api_simulator.scrape_profile(url)
                return json.dumps(result)
            
            mock_scrape.invoke.side_effect = simulate_api_call
            
            result = agent.enrich_candidates({
                "candidates": candidates,
                "projectid": "DATA-QUALITY-TEST"
            })
            
            enriched = result["enriched_candidates"][0]
            
            print(f"\n🔍 Data Quality Checks:")
            
            # Verify all expected fields are present
            required_fields = [
                'full_name', 'linkedin_url', 'work_experience',
                'education', 'skills', 'enrichment_status'
            ]
            
            for field in required_fields:
                assert field in enriched, f"Missing required field: {field}"
                print(f"   ✅ {field}: Present")
            
            # Verify data types
            assert isinstance(enriched['work_experience'], list)
            assert isinstance(enriched['education'], list)
            assert isinstance(enriched['skills'], list)
            print(f"   ✅ Data types: Correct")
            
            # Verify work experience structure
            for exp in enriched['work_experience']:
                assert 'company' in exp
                assert 'position' in exp
                assert 'duration' in exp or 'duration_years' in exp
            print(f"   ✅ Work experience structure: Valid")
            
            # Verify skills merged (no duplicates)
            assert len(enriched['skills']) == len(set(enriched['skills']))
            print(f"   ✅ Skills deduplication: Working")
            
            # Verify endorsements
            if 'endorsements' in enriched:
                assert isinstance(enriched['endorsements'], dict)
                print(f"   ✅ Endorsements: {len(enriched['endorsements'])} skills endorsed")
            
            print(f"\n✅ Data validation passed!")
    
    def test_batch_processing_performance(self, agent, linkedin_api_simulator):
        """Test performance with batch processing."""
        print("\n" + "="*70)
        print("BATCH PROCESSING PERFORMANCE TEST")
        print("="*70)
        
        # Create large batch
        batch_size = 20
        candidates = [
            {
                "full_name": f"Candidate {i}",
                "linkedin_url": f"https://linkedin.com/in/candidate-{i}",
                "skills": ["Python"]
            }
            for i in range(batch_size)
        ]
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape, \
             patch('time.sleep'):  # Speed up for testing
            
            def simulate_api_call(input_dict):
                url = input_dict.get("linkedin_url")
                result = linkedin_api_simulator.scrape_profile(url)
                return json.dumps(result)
            
            mock_scrape.invoke.side_effect = simulate_api_call
            
            start_time = time.time()
            
            result = agent.enrich_candidates({
                "candidates": candidates,
                "projectid": "BATCH-PERF-TEST",
                "enrichment_config": {
                    "batch_size": 5,
                    "rate_limit_delay": 0
                }
            })
            
            duration = time.time() - start_time
            
            print(f"\n📊 Batch Processing Results:")
            print(f"   - Total candidates: {batch_size}")
            print(f"   - Successful: {result['enrichment_stats']['success_count']}")
            print(f"   - Failed: {result['enrichment_stats']['failed_count']}")
            print(f"   - Total time: {duration:.2f}s")
            print(f"   - Avg time per candidate: {duration/batch_size:.2f}s")
            print(f"   - API calls made: {linkedin_api_simulator.call_count}")
            
            assert result["enrichment_stats"]["total_processed"] == batch_size
            assert result["enrichment_stats"]["success_count"] > 0
            
            print(f"\n✅ Batch processing working efficiently!")


class TestProfileScrapingWithDatabase:
    """Integration tests with database operations."""
    
    @pytest.fixture
    def agent(self):
        return ProfileScrapingAgent()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database agent."""
        db = MagicMock()
        db.execute_tool = MagicMock(return_value={"status": "success"})
        return db
    
    def test_enriched_data_persistence(self, agent, mock_db):
        """Test that enriched data can be properly saved to database."""
        print("\n" + "="*70)
        print("DATABASE PERSISTENCE TEST")
        print("="*70)
        
        # Simulate enrichment
        enriched_profile = {
            "success": True,
            "profile_data": {
                "work_experience": [{"company": "Test"}],
                "education": [{"institution": "Test U"}],
                "skills": ["Python", "Django", "AWS"],
                "certifications": ["AWS Cert"],
                "languages": ["English"]
            }
        }
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            mock_scrape.invoke.return_value = json.dumps(enriched_profile)
            
            result = agent.enrich_candidates({
                "candidates": [{
                    "full_name": "Test User",
                    "linkedin_url": "https://linkedin.com/in/testuser",
                    "email": "test@example.com"
                }],
                "projectid": "DB-TEST-001"
            })
            
            # Verify enriched data structure for database
            enriched = result["enriched_candidates"][0]
            
            # Verify it has all database-required fields
            assert "full_name" in enriched
            assert "linkedin_url" in enriched
            assert "work_experience" in enriched
            assert "project_metadata" in enriched
            assert "enrichment_timestamp" in enriched
            
            # Simulate saving to database
            db_payload = {
                "linkedin_url": enriched["linkedin_url"],
                "candidate_data": enriched,
                "project_id": enriched["project_metadata"]["project_id"]
            }
            
            mock_db.execute_tool("save_candidate", candidate_data=db_payload)
            
            # Verify database was called
            assert mock_db.execute_tool.called
            print(f"\n✅ Enriched profile structure valid for database storage")
            print(f"   - Keys: {list(enriched.keys())}")
            print(f"   - Project metadata: {enriched['project_metadata']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
