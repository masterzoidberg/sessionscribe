"""
Health endpoint tests for ASR service
"""

import pytest
import requests
from fastapi.testclient import TestClient
from services.asr.app import app

ASR_BASE_URL = "http://127.0.0.1:7035"

def test_health_ok():
    """Test health endpoint via TestClient"""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "asr"

def test_health_endpoint_live():
    """Test that live health endpoint returns correct status"""
    try:
        response = requests.get(f"{ASR_BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "asr"
        assert "whisper_model_ready" in data
        assert "recording" in data
        assert "transcribing" in data
        assert "active_connections" in data
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Live ASR service not available: {e}")

def test_health_endpoint_structure():
    """Test health endpoint returns all required fields"""
    try:
        response = requests.get(f"{ASR_BASE_URL}/health", timeout=5)
        data = response.json()
        
        required_fields = [
            "status", "service", "whisper_model_ready", 
            "recording", "transcribing", "active_connections"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check data types
        assert isinstance(data["whisper_model_ready"], bool)
        assert isinstance(data["recording"], bool)
        assert isinstance(data["transcribing"], bool)
        assert isinstance(data["active_connections"], int)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Live ASR service not available: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])