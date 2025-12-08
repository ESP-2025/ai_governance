"""
Backend API Test Suite

Tests all major API endpoints including health, prompt variants,
usage logging, alerts, and analytics.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.main import app
from app.models.database import Base, engine, SessionLocal
from app.models.schemas import UsageLogCreate, AlertCreate

# Test client
client = TestClient(app)

# Test API key
API_KEY = "dev-secret-key-change-in-production"

# Setup test database
@pytest.fixture(scope="module")
def setup_database():
    """Create tables for testing"""
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown (optional - comment out to preserve test data)
    # Base.metadata.drop_all(bind=engine)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test /health endpoint returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestPromptVariants:
    """Test prompt variant generation endpoints"""
    
    def test_generate_variants_success(self, setup_database):
        """Test generating prompt variants with valid input"""
        response = client.post(
            "/prompt-variants/",
            params={"original_prompt": "how to write clean code", "context": "chatgpt"},
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "variants" in data
        assert isinstance(data["variants"], list)
        assert len(data["variants"]) == 3
        
        # Verify each variant structure
        for variant in data["variants"]:
            assert "text" in variant
            assert "improvements" in variant
            assert "score" in variant
            assert isinstance(variant["text"], str)
            assert isinstance(variant["improvements"], list)
            assert isinstance(variant["score"], (int, float))
    
    def test_generate_variants_no_auth(self):
        """Test variant generation fails without API key"""
        response = client.post(
            "/prompt-variants/",
            params={"original_prompt": "test prompt"}
        )
        assert response.status_code == 403
    
    def test_generate_variants_empty_prompt(self, setup_database):
        """Test variant generation with empty prompt"""
        response = client.post(
            "/prompt-variants/",
            params={"original_prompt": ""},
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        # Should return empty variants for empty prompt
        assert len(data["variants"]) == 0


class TestUsageLogs:
    """Test usage logging endpoints"""
    
    def test_create_usage_log(self, setup_database):
        """Test creating a usage log"""
        log_data = {
            "user_email": "test@example.com",
            "tool": "chatgpt",
            "prompt_hash": "abc123",
            "risk_level": "low"
        }
        response = client.post(
            "/usage-logs/",
            json=log_data,
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 201
        data = response.json()
        
        # Verify response contains expected fields
        assert data["user_email"] == "test@example.com"
        assert data["tool"] == "chatgpt"
        assert data["risk_level"] == "low"
        assert "id" in data
        assert "timestamp" in data
    
    def test_create_usage_log_default_email(self, setup_database):
        """Test usage log creation with null email defaults to joshini.mn@gmail.com"""
        log_data = {
            "user_email": None,
            "tool": "claude",
            "prompt_hash": "def456",
            "risk_level": "medium"
        }
        response = client.post(
            "/usage-logs/",
            json=log_data,
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_email"] == "joshini.mn@gmail.com"
    
    def test_get_usage_logs(self, setup_database):
        """Test retrieving usage logs"""
        response = client.get(
            "/usage-logs/",
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have at least the logs we created


class TestAlerts:
    """Test alert endpoints"""
    
    def test_create_alert(self, setup_database):
        """Test creating a compliance alert"""
        alert_data = {
            "user_email": "test@example.com",
            "violation_type": "pii_detected",
            "details": {"pii_types": ["email", "ssn"], "tool": "chatgpt"}
        }
        response = client.post(
            "/alerts/",
            json=alert_data,
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 201
        data = response.json()
        
        # Verify alert structure
        assert data["violation_type"] == "pii_detected"
        assert "id" in data
        assert "timestamp" in data
        assert data["resolved"] is False
    
    def test_get_alerts(self, setup_database):
        """Test retrieving alerts"""
        response = client.get(
            "/alerts",
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAnalytics:
    """Test analytics endpoints"""
    
    def test_get_usage_analytics(self, setup_database):
        """Test usage analytics endpoint"""
        response = client.get(
            "/analytics/usage?days=7",
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify analytics structure
        assert "total_prompts" in data
        assert "unique_users" in data
        assert "prompts_by_tool" in data
        assert "prompts_by_risk" in data
        assert "top_users" in data
        
        # Verify data types
        assert isinstance(data["total_prompts"], int)
        assert isinstance(data["unique_users"], int)
        assert isinstance(data["prompts_by_tool"], dict)
        assert isinstance(data["top_users"], list)
    
    def test_analytics_custom_date_range(self, setup_database):
        """Test analytics with custom date range"""
        response = client.get(
            "/analytics/usage?days=30",
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200


class TestPromptLogging:
    """Test prompt choice logging"""
    
    def test_log_prompt_choice(self, setup_database):
        """Test logging user's variant selection"""
        log_data = {
            "user_email": "test@example.com",
            "original_prompt": "test original",
            "chosen_variant": "test improved",
            "variants": [
                {"text": "variant 1", "improvements": ["better"], "score": 85},
                {"text": "variant 2", "improvements": ["clearer"], "score": 90}
            ],
            "variant_index": 1
        }
        response = client.post(
            "/prompt-variants/log",
            json=log_data,
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify logged data
        assert data["original_prompt"] == "test original"
        assert data["chosen_variant"] == "test improved"
        assert data["variant_index"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
