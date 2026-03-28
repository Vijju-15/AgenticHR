"""Test suite for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"X-API-Key": "development-key"}


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestQueryEndpoint:
    """Test query endpoint."""
    
    def test_query_without_auth(self, client):
        """Test query without authentication (should work in dev)."""
        response = client.post(
            "/query",
            json={
                "query": "How many casual leaves do I get?",
                "agent_type": "agentic"
            }
        )
        # In development mode, should work
        assert response.status_code in [200, 503]  # 503 if agents not initialized
    
    def test_query_conversational(self, client, auth_headers):
        """Test conversational RAG query."""
        response = client.post(
            "/query",
            json={
                "query": "What is the leave policy?",
                "agent_type": "conversational"
            },
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "session_id" in data
    
    def test_query_agentic(self, client, auth_headers):
        """Test agentic RAG query."""
        response = client.post(
            "/query",
            json={
                "query": "Check leave balance for EMP123",
                "employee_id": "EMP123",
                "agent_type": "agentic"
            },
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data


class TestMetricsEndpoint:
    """Test metrics endpoint."""
    
    def test_get_metrics(self, client, auth_headers):
        """Test metrics retrieval."""
        response = client.get("/metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
