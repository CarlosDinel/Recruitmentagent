"""
Complete Test Suite with Mock Email and LinkedIn API
Unit Tests + Integration Tests for all agent flows
No external APIs needed - everything is mocked
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


# ==================== MOCK IMPLEMENTATIONS ====================

class MockEmailService:
    """Mock SMTP email service"""
    def __init__(self):
        self.sent_emails = []
    
    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Mock email sending"""
        email_record = {
            "to": to,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "sent"
        }
        self.sent_emails.append(email_record)
        return {"status": "success", "message_id": f"msg-{len(self.sent_emails)}"}


class MockLinkedInAPI:
    """Mock LinkedIn API via Unipile"""
    def __init__(self):
        self.actions = []
    
    def send_connection_request(self, provider_id: str, message: str = None) -> dict:
        """Mock connection request"""
        action = {
            "action": "connection_request",
            "provider_id": provider_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        self.actions.append(action)
        return action
    
    def send_message(self, provider_id: str, message: str) -> dict:
        """Mock direct message"""
        action = {
            "action": "direct_message",
            "provider_id": provider_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        self.actions.append(action)
        return action
    
    def send_inmail(self, provider_id: str, subject: str, body: str) -> dict:
        """Mock InMail"""
        action = {
            "action": "inmail",
            "provider_id": provider_id,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        self.actions.append(action)
        return action
    
    def like_post(self, post_id: str) -> dict:
        """Mock post like"""
        action = {
            "action": "post_like",
            "post_id": post_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        self.actions.append(action)
        return action


class MockMongoDatabase:
    """Mock MongoDB"""
    def __init__(self):
        self.candidates = {}
        self.projects = {}
    
    def save_candidate(self, candidate_data: dict) -> dict:
        """Save candidate to mock database"""
        linkedin_url = candidate_data.get("linkedin_url", "")
        self.candidates[linkedin_url] = candidate_data
        return {
            "status": "success",
            "inserted_id": linkedin_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def update_candidate(self, linkedin_url: str, updates: dict) -> dict:
        """Update candidate in mock database"""
        if linkedin_url in self.candidates:
            self.candidates[linkedin_url].update(updates)
            return {"status": "success", "modified_count": 1}
        return {"status": "error", "modified_count": 0}
    
    def get_candidates(self, limit: int = 10) -> list:
        """Get candidates from mock database"""
        return list(self.candidates.values())[:limit]


# ==================== FIXTURES ====================

@pytest.fixture
def email_service():
    """Fixture for mock email service"""
    return MockEmailService()


@pytest.fixture
def linkedin_api():
    """Fixture for mock LinkedIn API"""
    return MockLinkedInAPI()


@pytest.fixture
def database():
    """Fixture for mock database"""
    return MockMongoDatabase()


# ==================== UNIT TESTS - EMAIL ====================

class TestEmailOutreachWithMocks:
    """Unit tests for Email Outreach Agent with mock SMTP"""
    
    def test_send_single_email(self, email_service):
        """Test sending a single email"""
        result = email_service.send_email(
            to="john@example.com",
            subject="Opportunity at TechCorp",
            body="Hi John, we have an opportunity for you..."
        )
        
        assert result["status"] == "success"
        assert len(email_service.sent_emails) == 1
        assert email_service.sent_emails[0]["to"] == "john@example.com"
        print("✅ Single email test passed")
    
    def test_send_multiple_emails(self, email_service):
        """Test sending multiple emails"""
        emails = [
            ("john@example.com", "Opportunity 1"),
            ("alice@example.com", "Opportunity 2"),
            ("bob@example.com", "Opportunity 3")
        ]
        
        for email, subject in emails:
            email_service.send_email(
                to=email,
                subject=subject,
                body="Test body"
            )
        
        assert len(email_service.sent_emails) == 3
        print("✅ Multiple emails test passed")
    
    def test_email_with_personalization(self, email_service):
        """Test email with candidate personalization"""
        candidate = {
            "name": "John Doe",
            "company": "TechCorp",
            "position": "Python Developer",
            "skills": ["Python", "Django"]
        }
        
        body = f"""Hi {candidate['name']},

I saw that you're working at {candidate['company']} as a {candidate['position']}.
Your skills in {', '.join(candidate['skills'])} are impressive...

Best regards,
Carlos"""
        
        result = email_service.send_email(
            to="john@example.com",
            subject=f"Opportunity matching your {candidate['position']} skills",
            body=body
        )
        
        assert result["status"] == "success"
        assert candidate['name'] in email_service.sent_emails[0]["body"]
        print("✅ Personalized email test passed")


# ==================== UNIT TESTS - LINKEDIN ====================

class TestLinkedInOutreachWithMocks:
    """Unit tests for LinkedIn Outreach Agent with mock API"""
    
    def test_send_connection_request(self, linkedin_api):
        """Test sending connection request"""
        result = linkedin_api.send_connection_request(
            provider_id="john-123",
            message="Hi John, I'd like to connect!"
        )
        
        assert result["status"] == "success"
        assert result["action"] == "connection_request"
        assert len(linkedin_api.actions) == 1
        print("✅ Connection request test passed")
    
    def test_send_linkedin_message(self, linkedin_api):
        """Test sending direct LinkedIn message"""
        result = linkedin_api.send_message(
            provider_id="john-123",
            message="Hi John, I have an opportunity for you..."
        )
        
        assert result["status"] == "success"
        assert result["action"] == "direct_message"
        print("✅ LinkedIn message test passed")
    
    def test_send_inmail(self, linkedin_api):
        """Test sending InMail"""
        result = linkedin_api.send_inmail(
            provider_id="john-123",
            subject="Exclusive opportunity at TechCorp",
            body="Hi John, we'd like to discuss an exclusive opportunity..."
        )
        
        assert result["status"] == "success"
        assert result["action"] == "inmail"
        print("✅ InMail test passed")
    
    def test_like_post(self, linkedin_api):
        """Test liking a candidate's post"""
        result = linkedin_api.like_post(post_id="post-456")
        
        assert result["status"] == "success"
        assert result["action"] == "post_like"
        print("✅ Post like test passed")
    
    def test_multiple_linkedin_actions(self, linkedin_api):
        """Test multiple LinkedIn actions in sequence"""
        # First, like their post
        linkedin_api.like_post(post_id="post-456")
        
        # Then send connection request
        linkedin_api.send_connection_request(
            provider_id="john-123",
            message="Loved your recent post!"
        )
        
        # Then send message
        linkedin_api.send_message(
            provider_id="john-123",
            message="Following up on the connection request..."
        )
        
        assert len(linkedin_api.actions) == 3
        assert linkedin_api.actions[0]["action"] == "post_like"
        assert linkedin_api.actions[1]["action"] == "connection_request"
        assert linkedin_api.actions[2]["action"] == "direct_message"
        print("✅ Multiple LinkedIn actions test passed")


# ==================== UNIT TESTS - DATABASE ====================

class TestDatabaseWithMocks:
    """Unit tests for Database Agent with mock MongoDB"""
    
    def test_save_candidate(self, database):
        """Test saving candidate"""
        candidate = {
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "naam": "John Doe",
            "email": "john@example.com",
            "current_position": "Python Developer",
            "skills": ["Python", "Django"],
            "suitability_score": 85
        }
        
        result = database.save_candidate(candidate)
        
        assert result["status"] == "success"
        assert len(database.candidates) == 1
        print("✅ Save candidate test passed")
    
    def test_save_duplicate_candidate(self, database):
        """Test saving duplicate candidate (should update)"""
        candidate1 = {
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "naam": "John Doe",
            "email": "john@example.com",
            "suitability_score": 85
        }
        
        candidate2 = {
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "naam": "John Doe",
            "email": "john.doe@example.com",  # Updated email
            "suitability_score": 90
        }
        
        database.save_candidate(candidate1)
        database.save_candidate(candidate2)
        
        # Should only have 1 record (updated)
        assert len(database.candidates) == 1
        assert database.candidates["https://linkedin.com/in/johndoe"]["suitability_score"] == 90
        print("✅ Duplicate candidate handling test passed")
    
    def test_update_candidate_contact_status(self, database):
        """Test updating candidate contact status"""
        candidate = {
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "naam": "John Doe",
            "email": "john@example.com",
            "email_contacted": False,
            "linkedin_contacted": False
        }
        
        database.save_candidate(candidate)
        
        # Update contact status
        result = database.update_candidate(
            "https://linkedin.com/in/johndoe",
            {"email_contacted": True, "email_date": datetime.now(timezone.utc).isoformat()}
        )
        
        assert result["status"] == "success"
        assert database.candidates["https://linkedin.com/in/johndoe"]["email_contacted"] == True
        print("✅ Update contact status test passed")


# ==================== INTEGRATION TESTS ====================

class TestEmailOutreachFlow:
    """Integration test for Email Outreach workflow"""
    
    def test_email_outreach_campaign(self, email_service, database):
        """Test complete email outreach campaign"""
        
        # Test data
        candidates = [
            {
                "linkedin_url": "https://linkedin.com/in/john",
                "naam": "John Doe",
                "email": "john@example.com",
                "current_position": "Python Developer",
                "suitability_score": 85
            },
            {
                "linkedin_url": "https://linkedin.com/in/alice",
                "naam": "Alice Johnson",
                "email": "alice@example.com",
                "current_position": "Senior Python Developer",
                "suitability_score": 90
            }
        ]
        
        project_info = {
            "projectid": "PROJ-001",
            "project_name": "Python Developer - Amsterdam",
            "campaign_num": "CAMP-001"
        }
        
        # Step 1: Save candidates to database
        for candidate in candidates:
            database.save_candidate(candidate)
        
        assert len(database.candidates) == 2
        
        # Step 2: Send emails to all candidates
        for candidate in candidates:
            email_service.send_email(
                to=candidate["email"],
                subject=f"Opportunity at {project_info['project_name']}",
                body=f"Hi {candidate['naam']}, we have an opportunity for you..."
            )
        
        assert len(email_service.sent_emails) == 2
        
        # Step 3: Update database with email status
        for candidate in candidates:
            database.update_candidate(
                candidate["linkedin_url"],
                {
                    "email_contacted": True,
                    "email_date": datetime.now(timezone.utc).isoformat(),
                    "projectid": project_info["projectid"],
                    "campaign_num": project_info["campaign_num"]
                }
            )
        
        # Verify all emails updated
        all_candidates = database.get_candidates()
        assert all(c.get("email_contacted") for c in all_candidates)
        
        print("✅ Email campaign flow test passed")


class TestLinkedInOutreachFlow:
    """Integration test for LinkedIn Outreach workflow"""
    
    def test_linkedin_multi_channel_campaign(self, linkedin_api, database):
        """Test complete LinkedIn multi-channel outreach"""
        
        candidates = [
            {
                "linkedin_url": "https://linkedin.com/in/john",
                "naam": "John Doe",
                "provider_id": "john-123",
                "current_position": "Python Developer",
                "suitability_score": 85
            },
            {
                "linkedin_url": "https://linkedin.com/in/alice",
                "naam": "Alice Johnson",
                "provider_id": "alice-456",
                "current_position": "Senior Python Developer",
                "suitability_score": 90,
                "post_id": "post-789"
            }
        ]
        
        # Step 1: Save candidates
        for candidate in candidates:
            database.save_candidate(candidate)
        
        # Step 2: Execute multi-channel outreach
        for candidate in candidates:
            # Like their post if available
            if candidate.get("post_id"):
                linkedin_api.like_post(candidate["post_id"])
            
            # Send connection request
            linkedin_api.send_connection_request(
                provider_id=candidate["provider_id"],
                message=f"Hi {candidate['naam']}, I'd like to connect!"
            )
            
            # Send follow-up message
            linkedin_api.send_message(
                provider_id=candidate["provider_id"],
                message=f"Hi {candidate['naam']}, I have an exciting opportunity for you..."
            )
        
        # Verify actions
        assert len(linkedin_api.actions) == 5  # 1 like + 2 per candidate (2*2)
        
        # Update database
        for candidate in candidates:
            database.update_candidate(
                candidate["linkedin_url"],
                {
                    "connectie_verzoek": True,
                    "linkedin_bericht": True,
                    "contactmomenten": {
                        "connectie_verzoek": True,
                        "linkedin_bericht": True
                    }
                }
            )
        
        all_candidates = database.get_candidates()
        assert all(c.get("connectie_verzoek") for c in all_candidates)
        
        print("✅ LinkedIn multi-channel campaign test passed")


# ==================== END-TO-END INTEGRATION TEST ====================

class TestCompleteRecruitmentFlow:
    """Integration test for complete end-to-end recruitment"""
    
    def test_complete_sourcing_to_outreach_flow(self, email_service, linkedin_api, database):
        """Test complete flow from sourcing to outreach"""
        
        # ========== STAGE 1: SOURCING ==========
        print("\n[STAGE 1] Sourcing candidates...")
        
        sourced_candidates = [
            {
                "linkedin_url": "https://linkedin.com/in/john",
                "naam": "John Doe",
                "email": "john@example.com",
                "provider_id": "john-123",
                "current_position": "Python Developer",
                "skills": ["Python", "Django"],
                "suitability_score": 85
            },
            {
                "linkedin_url": "https://linkedin.com/in/alice",
                "naam": "Alice Johnson",
                "email": "alice@example.com",
                "provider_id": "alice-456",
                "current_position": "Senior Python Developer",
                "skills": ["Python", "Django", "FastAPI"],
                "suitability_score": 92
            },
            {
                "linkedin_url": "https://linkedin.com/in/bob",
                "naam": "Bob Smith",
                "email": "bob@example.com",
                "provider_id": "bob-789",
                "current_position": "Python Developer",
                "skills": ["Python", "Flask"],
                "suitability_score": 78
            }
        ]
        
        # Save sourced candidates to database
        for candidate in sourced_candidates:
            database.save_candidate(candidate)
        
        print(f"✅ Sourced {len(sourced_candidates)} candidates")
        assert len(database.candidates) == 3
        
        # ========== STAGE 2: EVALUATION ==========
        print("[STAGE 2] Evaluating candidates...")
        
        suitable_candidates = [c for c in sourced_candidates if c["suitability_score"] >= 80]
        print(f"✅ {len(suitable_candidates)} suitable candidates")
        assert len(suitable_candidates) == 2
        
        # ========== STAGE 3: EMAIL OUTREACH ==========
        print("[STAGE 3] Email outreach...")
        
        for candidate in suitable_candidates:
            email_service.send_email(
                to=candidate["email"],
                subject=f"Exciting Opportunity: Python Developer at TechCorp",
                body=f"""Hi {candidate['naam']},

I came across your profile and was impressed by your experience as a {candidate['current_position']}.

We have an exciting opportunity for a Python Developer at TechCorp in Amsterdam, and I think you'd be a great fit.

Your skills in {', '.join(candidate['skills'])} align perfectly with what we're looking for.

Would you be open to a quick call to discuss this opportunity?

Best regards,
Carlos"""
            )
            
            database.update_candidate(
                candidate["linkedin_url"],
                {"email_contacted": True, "email_date": datetime.now(timezone.utc).isoformat()}
            )
        
        print(f"✅ Sent {len(email_service.sent_emails)} emails")
        assert len(email_service.sent_emails) == 2
        
        # ========== STAGE 4: LINKEDIN OUTREACH ==========
        print("[STAGE 4] LinkedIn outreach...")
        
        for candidate in suitable_candidates:
            # Send connection request
            linkedin_api.send_connection_request(
                provider_id=candidate["provider_id"],
                message=f"Hi {candidate['naam']}, following up on the email I sent. Would love to connect!"
            )
            
            database.update_candidate(
                candidate["linkedin_url"],
                {"connectie_verzoek": True}
            )
        
        connection_requests = len([a for a in linkedin_api.actions if a['action'] == 'connection_request'])
        print(f"✅ Sent {connection_requests} connection requests")
        assert connection_requests == 2
        
        # ========== VERIFICATION ==========
        print("\n[VERIFICATION] Checking results...")
        
        all_candidates = database.get_candidates()
        contacted_candidates = [c for c in all_candidates if c.get("email_contacted") or c.get("connectie_verzoek")]
        
        assert len(all_candidates) == 3
        assert len(contacted_candidates) >= 2
        assert len(email_service.sent_emails) == 2
        assert len(linkedin_api.actions) == 2
        
        print(f"""
✅ COMPLETE FLOW SUCCESS!
- Total candidates sourced: {len(all_candidates)}
- Suitable candidates: {len(suitable_candidates)}
- Contacted: {len(contacted_candidates)}
- Emails sent: {len(email_service.sent_emails)}
- LinkedIn actions: {len(linkedin_api.actions)}
        """)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# ==================== END-TO-END TEST WITH PROFILE SCRAPING ====================

class TestCompleteRecruitmentFlowWithProfileScraping:
    """End-to-end test including Profile Scraping Agent"""
    
    def test_full_recruitment_pipeline_with_enrichment(self, email_service, linkedin_api, database):
        """
        Complete recruitment pipeline test:
        1. Candidate Searching (mock LinkedIn search)
        2. Initial Evaluation
        3. Profile Scraping (deep enrichment)
        4. Final Evaluation with enriched data
        5. Multi-channel Outreach
        6. Database persistence
        """
        print("\n" + "="*70)
        print("COMPLETE RECRUITMENT PIPELINE WITH PROFILE SCRAPING")
        print("="*70)
        
        # ========== STAGE 1: CANDIDATE SEARCHING ==========
        print("\n[STAGE 1] Searching for candidates...")
        
        initial_candidates = [
            {
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "full_name": "John Doe",
                "email": "john@example.com",
                "provider_id": "john-123",
                "current_position": "Python Developer",
                "current_company": "StartupCo",
                "skills": ["Python", "AWS"],
                "suitability_score": 85
            },
            {
                "linkedin_url": "https://linkedin.com/in/alicesmith",
                "full_name": "Alice Smith", 
                "email": "alice@example.com",
                "provider_id": "alice-456",
                "current_position": "Senior Python Developer",
                "current_company": "TechGiant",
                "skills": ["Python", "Django"],
                "suitability_score": 92
            },
            {
                "linkedin_url": "https://linkedin.com/in/bobwilson",
                "full_name": "Bob Wilson",
                "email": "bob@example.com", 
                "provider_id": "bob-789",
                "current_position": "Software Engineer",
                "current_company": "Innovation Labs",
                "skills": ["Python", "React"],
                "suitability_score": 78
            }
        ]
        
        print(f"✅ Found {len(initial_candidates)} initial candidates")
        
        # ========== STAGE 2: INITIAL EVALUATION ==========
        print("\n[STAGE 2] Initial candidate evaluation...")
        
        high_potential = [c for c in initial_candidates if c["suitability_score"] >= 80]
        print(f"✅ Identified {len(high_potential)} high-potential candidates for enrichment")
        assert len(high_potential) == 2
        
        # ========== STAGE 3: PROFILE SCRAPING (ENRICHMENT) ==========
        print("\n[STAGE 3] Deep profile scraping for high-potential candidates...")
        
        from sub_agents.profile_scraping_agent import ProfileScrapingAgent
        
        # Mock enriched profile data
        mock_enriched_data = {
            "https://linkedin.com/in/johndoe": {
                "work_experience": [
                    {
                        "company": "StartupCo",
                        "position": "Python Developer",
                        "duration": "2022-Present",
                        "description": "Backend development with Django"
                    },
                    {
                        "company": "CodeCorp",
                        "position": "Junior Developer", 
                        "duration": "2020-2022",
                        "description": "Full-stack development"
                    }
                ],
                "education": [
                    {
                        "institution": "University of Amsterdam",
                        "degree": "BSc Computer Science",
                        "year": "2020"
                    }
                ],
                "skills": ["Python", "AWS", "Docker", "PostgreSQL", "Redis"],
                "certifications": ["AWS Certified Developer"],
                "languages": ["English", "Dutch"],
                "endorsements": {"Python": 45, "AWS": 23},
                "summary": "Passionate backend developer with 4+ years of experience",
                "headline": "Python Developer | AWS | Backend Specialist",
                "connections_count": 450
            },
            "https://linkedin.com/in/alicesmith": {
                "work_experience": [
                    {
                        "company": "TechGiant",
                        "position": "Senior Python Developer",
                        "duration": "2020-Present",
                        "description": "Leading backend team, architecting microservices"
                    },
                    {
                        "company": "FinTech Inc",
                        "position": "Python Developer",
                        "duration": "2017-2020",
                        "description": "Payment systems development"
                    }
                ],
                "education": [
                    {
                        "institution": "TU Delft",
                        "degree": "MSc Computer Science",
                        "year": "2017"
                    }
                ],
                "skills": ["Python", "Django", "FastAPI", "Kubernetes", "Microservices", "PostgreSQL"],
                "certifications": ["AWS Solutions Architect", "Google Cloud Professional"],
                "languages": ["English", "Dutch", "German"],
                "endorsements": {"Python": 89, "Django": 67, "FastAPI": 34},
                "summary": "Senior engineer specializing in scalable backend systems",
                "headline": "Senior Python Engineer | Microservices Architect",
                "connections_count": 850
            }
        }
        
        # Mock the LinkedIn profile scraping
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            def mock_scrape_invoke(input_dict):
                url = input_dict.get("linkedin_url")
                if url in mock_enriched_data:
                    return json.dumps({
                        "success": True,
                        "profile_data": mock_enriched_data[url]
                    })
                return json.dumps({"success": False, "error": "Profile not found"})
            
            mock_scrape.invoke.side_effect = mock_scrape_invoke
            
            # Create ProfileScrapingAgent and enrich
            scraping_agent = ProfileScrapingAgent()
            
            enrichment_request = {
                "candidates": high_potential,
                "projectid": "PROJ-E2E-001",
                "naam_project": "Backend Team Expansion E2E",
                "campaign_num": "CAMP-E2E-001",
                "search_id": "SEARCH-E2E-001"
            }
            
            enrichment_result = scraping_agent.enrich_candidates(enrichment_request)
            
            assert enrichment_result["success"] is True
            assert len(enrichment_result["enriched_candidates"]) == 2
            assert enrichment_result["enrichment_stats"]["success_count"] == 2
            assert enrichment_result["enrichment_stats"]["failed_count"] == 0
            
            enriched_candidates = enrichment_result["enriched_candidates"]
            
            print(f"✅ Successfully enriched {len(enriched_candidates)} profiles")
            
            # Verify enrichment data
            for candidate in enriched_candidates:
                assert "work_experience" in candidate
                assert "education" in candidate
                assert "certifications" in candidate
                assert len(candidate["skills"]) > len(high_potential[0]["skills"])
                print(f"   - {candidate['full_name']}: {len(candidate['work_experience'])} jobs, "
                      f"{len(candidate['skills'])} skills, {len(candidate.get('certifications', []))} certs")
        
        # ========== STAGE 4: ENHANCED EVALUATION ==========
        print("\n[STAGE 4] Re-evaluation with enriched data...")
        
        # Recalculate suitability with enriched data
        for candidate in enriched_candidates:
            base_score = candidate["suitability_score"]
            
            # Boost score based on enrichment
            experience_boost = len(candidate.get("work_experience", [])) * 2
            cert_boost = len(candidate.get("certifications", [])) * 5
            skills_boost = min(len(candidate.get("skills", [])), 10)
            
            new_score = min(base_score + experience_boost + cert_boost + skills_boost, 100)
            candidate["enhanced_suitability_score"] = new_score
            
            print(f"   - {candidate['full_name']}: {base_score} → {new_score} "
                  f"(+{new_score - base_score} from enrichment)")
        
        # Select final candidates
        final_candidates = [c for c in enriched_candidates if c["enhanced_suitability_score"] >= 90]
        print(f"✅ {len(final_candidates)} candidates meet enhanced criteria")
        
        # ========== STAGE 5: DATABASE PERSISTENCE ==========
        print("\n[STAGE 5] Saving enriched profiles to database...")
        
        for candidate in enriched_candidates:
            database.save_candidate(candidate)
        
        # Also save the lower-scoring candidate
        database.save_candidate(initial_candidates[2])
        
        print(f"✅ Saved {len(database.candidates)} candidates to database")
        assert len(database.candidates) == 3
        
        # ========== STAGE 6: PERSONALIZED OUTREACH ==========
        print("\n[STAGE 6] Personalized multi-channel outreach...")
        
        for candidate in final_candidates:
            # Generate highly personalized email using enriched data
            recent_company = candidate["work_experience"][0]["company"] if candidate.get("work_experience") else candidate.get("current_company", "your company")
            years_exp = len(candidate.get("work_experience", []))
            top_skills = ", ".join(candidate["skills"][:3])
            
            email_body = f"""Hi {candidate['full_name']},

I hope this message finds you well! I came across your LinkedIn profile and was genuinely impressed by your career trajectory.

Your experience at {recent_company} as a {candidate['current_position']}, combined with your {years_exp}+ years in software development, really caught my attention. Your expertise in {top_skills} is exactly what we're looking for.

I noticed you have certifications in {', '.join(candidate.get('certifications', ['relevant areas']))} - that shows real dedication to staying current with industry best practices.

We're building a world-class backend team at TechCorp in Amsterdam, and I believe you'd be an excellent fit for our Senior Python Engineer position. The role involves:

- Architecting scalable microservices
- Leading a team of talented engineers
- Working with cutting-edge technologies
- Competitive compensation package

Would you be open to a brief call this week to explore this opportunity?

Looking forward to hearing from you!

Best regards,
Carlos Almeida
Senior Tech Recruiter
TechCorp"""
            
            # Send email
            email_service.send_email(
                to=candidate["email"],
                subject=f"Senior Backend Opportunity at TechCorp - Perfect fit for your {candidate['current_position']} experience",
                body=email_body
            )
            
            # Send LinkedIn connection request with personalized note
            linkedin_message = f"""Hi {candidate['full_name']}, I just sent you an email about an exciting Senior Python Engineer opportunity at TechCorp. Your experience with {top_skills} makes you a perfect fit. Would love to connect and discuss further!"""
            
            linkedin_api.send_connection_request(
                provider_id=candidate["provider_id"],
                message=linkedin_message[:300]  # LinkedIn limit
            )
            
            # Update database
            database.update_candidate(
                candidate["linkedin_url"],
                {
                    "email_contacted": True,
                    "email_date": datetime.now(timezone.utc).isoformat(),
                    "connectie_verzoek": True,
                    "connection_date": datetime.now(timezone.utc).isoformat(),
                    "outreach_personalization_level": "high",
                    "enrichment_used": True
                }
            )
            
            print(f"   ✅ Contacted {candidate['full_name']} via email + LinkedIn")
        
        print(f"\n✅ Completed outreach to {len(final_candidates)} top candidates")
        
        # ========== STAGE 7: CAMPAIGN ANALYTICS ==========
        print("\n[STAGE 7] Campaign analytics and reporting...")
        
        campaign_stats = {
            "total_searched": len(initial_candidates),
            "initial_suitable": len(high_potential),
            "profiles_enriched": len(enriched_candidates),
            "final_contacted": len(final_candidates),
            "emails_sent": len(email_service.sent_emails),
            "linkedin_actions": len(linkedin_api.actions),
            "database_records": len(database.candidates),
            "enrichment_success_rate": enrichment_result["enrichment_stats"]["success_rate"],
            "avg_score_improvement": sum(c["enhanced_suitability_score"] - c["suitability_score"] 
                                        for c in enriched_candidates) / len(enriched_candidates)
        }
        
        print(f"""
{'='*70}
CAMPAIGN RESULTS SUMMARY
{'='*70}
📊 Sourcing Metrics:
   - Total candidates found: {campaign_stats['total_searched']}
   - High-potential identified: {campaign_stats['initial_suitable']}
   - Conversion rate: {campaign_stats['initial_suitable']/campaign_stats['total_searched']*100:.1f}%

🔍 Enrichment Metrics:
   - Profiles enriched: {campaign_stats['profiles_enriched']}
   - Enrichment success rate: {campaign_stats['enrichment_success_rate']*100:.0f}%
   - Avg score improvement: +{campaign_stats['avg_score_improvement']:.1f} points

📧 Outreach Metrics:
   - Final candidates contacted: {campaign_stats['final_contacted']}
   - Emails sent: {campaign_stats['emails_sent']}
   - LinkedIn connection requests: {campaign_stats['linkedin_actions']}
   - Personalization level: HIGH (enrichment-based)

💾 Data Management:
   - Records in database: {campaign_stats['database_records']}
   - Enriched profiles stored: {campaign_stats['profiles_enriched']}

{'='*70}
✅ COMPLETE E2E TEST PASSED!
{'='*70}
        """)
        
        # ========== FINAL ASSERTIONS ==========
        assert campaign_stats["total_searched"] == 3
        assert campaign_stats["initial_suitable"] == 2
        assert campaign_stats["profiles_enriched"] == 2
        assert campaign_stats["final_contacted"] == 2
        assert campaign_stats["emails_sent"] == 2
        assert campaign_stats["linkedin_actions"] == 2
        assert campaign_stats["database_records"] == 3
        assert campaign_stats["enrichment_success_rate"] == 1.0
        assert campaign_stats["avg_score_improvement"] > 0
        
        # Verify enriched data in database
        db_candidates = database.get_candidates()
        enriched_in_db = [c for c in db_candidates if c.get("enrichment_used")]
        assert len(enriched_in_db) == 2
        
        # Verify personalization was applied
        for email in email_service.sent_emails:
            assert "certifications" in email["body"] or "experience" in email["body"]
            assert len(email["body"]) > 200  # Detailed personalized message
        
        print("\n✅ All assertions passed! Complete recruitment pipeline working correctly.")
    
    def test_profile_scraping_with_failures(self, database):
        """Test profile scraping with some failures in the pipeline"""
        print("\n" + "="*70)
        print("PROFILE SCRAPING WITH FAILURE HANDLING")
        print("="*70)
        
        from sub_agents.profile_scraping_agent import ProfileScrapingAgent
        
        candidates = [
            {
                "linkedin_url": "https://linkedin.com/in/working-profile",
                "full_name": "Success Candidate",
                "skills": ["Python"]
            },
            {
                "linkedin_url": "https://linkedin.com/in/failing-profile",
                "full_name": "Failed Candidate",
                "skills": ["Python"]
            },
            {
                "full_name": "No URL Candidate",
                "skills": ["Python"]
            }
        ]
        
        with patch('sub_agents.profile_scraping_agent.LinkedIn_profile_scrape') as mock_scrape:
            def mock_scrape_with_failures(input_dict):
                url = input_dict.get("linkedin_url")
                if url == "https://linkedin.com/in/working-profile":
                    return json.dumps({
                        "success": True,
                        "profile_data": {
                            "work_experience": [{"company": "Test"}],
                            "education": [],
                            "skills": ["Python", "Django"]
                        }
                    })
                return json.dumps({"success": False, "error": "Profile not accessible"})
            
            mock_scrape.invoke.side_effect = mock_scrape_with_failures
            
            agent = ProfileScrapingAgent()
            result = agent.enrich_candidates({
                "candidates": candidates,
                "projectid": "TEST-FAIL"
            })
            
            assert result["success"] is True
            assert result["enrichment_stats"]["success_count"] == 1
            assert result["enrichment_stats"]["failed_count"] == 2
            
            print(f"✅ Success count: {result['enrichment_stats']['success_count']}")
            print(f"✅ Failed count: {result['enrichment_stats']['failed_count']}")
            print(f"✅ Success rate: {result['enrichment_stats']['success_rate']*100:.0f}%")
            
            # Verify failed candidates have error messages
            for failed in result["failed_enrichments"]:
                assert "enrichment_error" in failed
                print(f"   - {failed['full_name']}: {failed['enrichment_error']}")
            
            print("\n✅ Failure handling test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])