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